import os, tempfile, math
os.environ['ADMIN_TOKEN']='test-secret-at-least-24-characters'
os.environ['DATA_DIR']=tempfile.mkdtemp()
from fastapi.testclient import TestClient
from app.main import app
from app.engine import simulate
H={'Authorization':'Bearer '+os.environ['ADMIN_TOKEN']}
def test_physics():
    assert math.isclose(simulate({'gain':2,'tau':1,'duration':5})['final_value'],1.986524106001829)
def test_auth_and_validation():
    with TestClient(app) as c:
        assert c.get('/api/runs').status_code==401
        assert c.get('/api/runs',headers=H).status_code==200
        assert c.post('/api/runs',headers=H,json={'mode':'unknown'}).status_code==422
        assert c.post('/api/runs',headers=H,json={'mode':'llm'}).status_code==400
        assert c.post('/mcp',headers=H,json={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'simulate_first_order','arguments':{'gain':2,'tau':0,'duration':5}}}).json()['result']['isError']
        assert c.post('/mcp',headers={**H,'Origin':'https://evil.example'},json={}).status_code==403
        assert c.get('/api/runs/missing',headers=H).status_code==404
