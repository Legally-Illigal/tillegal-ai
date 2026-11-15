"""Additional read-only scenarios; uses verifier's identical configuration/GET guard."""
from pathlib import Path
import sys
import json
import asyncio
import subprocess

launcher=Path(__file__).with_name('retrieval-e2e-verifier.py').resolve()
# Load only the existing verifier's setup, stopping before its CLI/main execution.
setup=launcher.read_text(encoding='utf-8').split("if len(sys.argv)>1 and sys.argv[1]=='--cli-child':")[0]
exec(compile(setup, str(launcher), 'exec'))
from src.retrieval_bootstrap import create_retrieval_service
from src.applications.tillegal.retrieval.contracts import RetrievalRequest
from pydantic import ValidationError

path=ROOT/'.docs/development/retrieval-e2e-evidence.json'
r=json.loads(path.read_text(encoding='utf-8'))
for mode in ('bm25','dense','hybrid'):
    try:
        RetrievalRequest(query=r['query'],mode=mode,top_k=0,as_of_date=r['as_of_date'],allowed_usage_policies=r['allowed_policies'])
        rejected=False
    except ValidationError:
        rejected=True
    r['tests'].append({'id':mode+'_invalid_request','rejected':rejected,'real_db_operations':False})
    svc=create_retrieval_service(settings,dense_model_path=MODEL)
    # Deliberate local configuration fault; no database or production config changed.
    if mode=='bm25': svc._index_name='audit-deliberately-unavailable-index'
    else: svc._dense_index_name='audit-deliberately-unavailable-index'
    trace.clear()
    req=RetrievalRequest(query=r['query'],mode=mode,top_k=5,as_of_date=r['as_of_date'],allowed_usage_policies=r['allowed_policies'])
    resp=asyncio.run(svc.search(req))
    raw=resp.model_dump(mode='json')
    r['tests'].append({'id':mode+'_controlled_missing_index','kind':'actual_service_local_index_configuration_fault',
        'status':raw['status'],'error':raw['error'],'evidence_count':len(resp.evidence),'rpc_calls':list(trace),
        'no_partial_evidence':raw['status']=='FAILED' and not resp.evidence,
        'fusion_branches':raw.get('fusion',{}).get('branches')})
    args=['--query',r['query'],'--mode',mode,'--top-k','0','--as-of-date',r['as_of_date'],'--allowed-policy','EXPERIMENTAL_ONLY']
    proc=subprocess.run([sys.executable,str(launcher),'--cli-child',*args],capture_output=True,text=True,encoding='utf-8',timeout=30)
    raw=json.loads(proc.stdout)
    r['tests'].append({'id':'cli_'+mode+'_invalid','exit_code':proc.returncode,'response':raw,'real_db_operations':False})
    print(json.dumps({'mode':mode,'invalid_rejected':rejected,'missing_index_status':resp.status,'cli_invalid_exit':proc.returncode}),flush=True)
path.write_text(json.dumps(r,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
