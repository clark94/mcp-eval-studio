import json, os, secrets, sqlite3, threading, time, uuid
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict
from typing import Literal
from app.engine import TOOL, simulate, evaluate
ROOT=Path(os.getenv("DATA_DIR","./data")); ROOT.mkdir(parents=True,exist_ok=True)
TOKEN=os.getenv("ADMIN_TOKEN","")
if len(TOKEN)<24: raise RuntimeError("Set ADMIN_TOKEN to a random secret of at least 24 characters")
def db():
    c=sqlite3.connect(ROOT/"studio.db",timeout=30); c.row_factory=sqlite3.Row; return c
def init():
    with db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,created REAL,status TEXT,config TEXT,result TEXT)")
        c.execute("UPDATE jobs SET status='interrupted' WHERE status='running'")
def worker():
    while True:
        with db() as c:
            row=c.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
            if row: c.execute("UPDATE jobs SET status='running' WHERE id=?",(row['id'],))
        if not row: time.sleep(.5); continue
        try: result=evaluate(**json.loads(row['config'])); status='completed'
        except Exception: result={"error":"Execution failed. Check MCP/LLM service configuration."}; status='failed'
        with db() as c: c.execute("UPDATE jobs SET status=?,result=? WHERE id=?",(status,json.dumps(result),row['id']))
@asynccontextmanager
async def lifespan(app):
    init(); threading.Thread(target=worker,daemon=True).start(); yield
app=FastAPI(title="MCP Eval Studio",version="1.0.0",lifespan=lifespan,docs_url=None,redoc_url=None)
security=HTTPBearer(auto_error=False)
def auth(cred: HTTPAuthorizationCredentials=Depends(security)):
    if not cred or not secrets.compare_digest(cred.credentials,TOKEN): raise HTTPException(401,"Authentication required")
@app.middleware("http")
async def secure(request,call_next):
    origin=request.headers.get('origin')
    if origin and origin not in os.getenv('ALLOWED_ORIGINS','http://localhost:8000,http://127.0.0.1:8000').split(','): return Response(status_code=403)
    r=await call_next(request)
    r.headers['X-Content-Type-Options']='nosniff';r.headers['Referrer-Policy']='no-referrer';r.headers['X-Frame-Options']='DENY'
    r.headers['Cache-Control']='no-store'
    return r
@app.get('/health')
def health(): return {"status":"ok","simulator":"demo"}
@app.get('/',response_class=HTMLResponse)
def index(): return Path(__file__).with_name('index.html').read_text()
class Run(BaseModel):
    model_config=ConfigDict(extra='forbid')
    mode: Literal['reference','llm']='reference'
    judge: bool=False
@app.post('/api/runs',dependencies=[Depends(auth)],status_code=202)
def create(config:Run):
    if (config.mode=='llm' or config.judge) and not (os.getenv('LLM_API_KEY') and os.getenv('LLM_MODEL')): raise HTTPException(400,'Configure LLM_API_KEY and LLM_MODEL on server')
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        if c.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0]>=3: raise HTTPException(429,'Queue full: maximum 3 active runs')
        ident=str(uuid.uuid4());c.execute('INSERT INTO jobs VALUES(?,?,?,?,NULL)',(ident,time.time(),'queued',config.model_dump_json()))
    return {"id":ident}
@app.get('/api/runs',dependencies=[Depends(auth)])
def runs():
    with db() as c: return [dict(r) for r in c.execute('SELECT id,created,status,config FROM jobs ORDER BY created DESC LIMIT 100')]
@app.get('/api/runs/{ident}',dependencies=[Depends(auth)])
def detail(ident:str):
    with db() as c: row=c.execute('SELECT * FROM jobs WHERE id=?',(ident,)).fetchone()
    if not row: raise HTTPException(404)
    r=dict(row);r['result']=json.loads(r['result']) if r['result'] else None; return r
@app.get('/api/runs/{ident}/export',dependencies=[Depends(auth)])
def export(ident:str):
    return Response(json.dumps(detail(ident),ensure_ascii=False,indent=2),media_type='application/json',headers={'Content-Disposition':'attachment; filename="evaluation.json"'})
@app.post('/mcp',dependencies=[Depends(auth)])
def mcp(body:dict):
    ident=body.get('id');method=body.get('method');params=body.get('params',{})
    if method=='notifications/initialized': return Response(status_code=202)
    if body.get('jsonrpc')!='2.0': return {"jsonrpc":"2.0","id":ident,"error":{"code":-32600,"message":"Invalid request"}}
    if method=='initialize': result={"protocolVersion":"2025-11-25","capabilities":{"tools":{}},"serverInfo":{"name":"first-order-demo","version":"1.0"}}
    elif method=='ping': result={}
    elif method=='tools/list': result={"tools":[TOOL]}
    elif method=='tools/call':
        try:
            if params.get('name')!=TOOL['name']: raise ValueError('Unknown tool')
            data=simulate(params.get('arguments',{}));result={"content":[{"type":"text","text":json.dumps(data)}],"isError":False}
        except (ValueError,TypeError,KeyError,OverflowError): result={"content":[{"type":"text","text":"Invalid tool or parameters"}],"isError":True}
    else: return {"jsonrpc":"2.0","id":ident,"error":{"code":-32601,"message":"Method not found"}}
    return {"jsonrpc":"2.0","id":ident,"result":result}
