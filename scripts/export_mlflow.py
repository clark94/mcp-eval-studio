"""Import an exported evaluation into an existing MLflow tracking backend."""
import json, sys, statistics
import mlflow
from pathlib import Path
path=Path(sys.argv[1]); exported=json.loads(path.read_text());r=exported.get('result',exported)
if not r or not r.get('total'): raise SystemExit('A completed evaluation report is required')
mlflow.set_experiment('MCP Eval Studio')
with mlflow.start_run():
    mlflow.log_params({'mode':r['mode'],'model':r['model'],'simulator':'first_order_demo'})
    mlflow.log_metrics({'pass_rate':r['passed']/r['total'],'latency_ms_mean':statistics.mean(x['latency_ms'] for x in r['results'])})
    mlflow.log_artifact(str(path))
    print('Exported MLflow run:',mlflow.active_run().info.run_id)
