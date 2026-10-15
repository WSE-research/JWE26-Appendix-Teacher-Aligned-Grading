"""Frozen rationale-only collection. No scoring, human labels, or automatic retries."""
import argparse, base64, hashlib, json, os, time
from pathlib import Path
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from urllib.error import HTTPError
from urllib.parse import urlparse
import fcntl

LABELS=['supports_correct','supports_incorrect','undetermined']
SCHEMA={'type':'object','properties':{'label':{'type':'string','enum':LABELS},'evidence':{'type':'string','minLength':1}},'required':['label','evidence'],'additionalProperties':False}
def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def append(path,row):
    with path.open('ab') as f:f.write(canonical(row)+b'\n');f.flush();os.fsync(f.fileno())
def parse(body,reason):
    choices=body['choices']
    if len(choices)!=1 or choices[0]['finish_reason']!='stop':raise ValueError('Not one complete generation')
    msg=choices[0]['message']
    if msg.get('reasoning') or msg.get('reasoning_content'):raise ValueError('Unexpected reasoning output')
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:raise ValueError('Duplicate JSON key')
            d[k]=v
        return d
    v=json.loads(msg['content'],object_pairs_hook=unique)
    if not isinstance(v,dict) or set(v)!= {'label','evidence'}:raise ValueError('Schema keys')
    if v['label'] not in LABELS or not isinstance(v['evidence'],str) or not v['evidence'].strip() or v['evidence'] not in reason:raise ValueError('Invalid label or quote')
    return v

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def urlopen(request,timeout):
    return build_opener(ProxyHandler({}),NoRedirect()).open(request,timeout=timeout)

def atomic(path,data):
    tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    tmp.replace(path)
    fd=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)

def request_for(manifest,prompt,reason):
    return {'model':manifest['model'],'temperature':0,'max_tokens':256,'chat_template_kwargs':{'enable_thinking':False},'messages':[{'role':'system','content':prompt.decode()},{'role':'user','content':json.dumps({'reason':reason},ensure_ascii=False)}],'response_format':{'type':'json_schema','json_schema':{'name':'rationale_stance','strict':True,'schema':SCHEMA}}}

def response_verdict(event,reason,model):
    raw=base64.b64decode(event['raw_response_base64'],validate=True)
    if sha(raw)!=event['response_sha256']:raise ValueError('Raw response hash mismatch')
    if event['http_status']!=200:raise ValueError('Non-200 response retained')
    body=json.loads(raw)
    if body.get('model')!=model:raise ValueError('Unexpected served model')
    return parse(body,reason)

def collect(package,stage,output,base_url):
    u=urlparse(base_url)
    if u.scheme!='http' or u.hostname!='127.0.0.1' or u.username or u.password or u.path not in ('','/') or u.query or u.fragment:raise ValueError('Only loopback serving allowed')
    manifest=json.loads((package/'manifest.json').read_text())
    prompt=(package/'prompt.txt').read_bytes()
    if sha(prompt)!=manifest['prompt_sha256']:raise ValueError('Prompt drift')
    name='sample_blind.jsonl' if stage=='sample' else 'all_blind.jsonl'
    raw=(package/name).read_bytes()
    if sha(raw)!=manifest['input_sha256'][name]:raise ValueError('Input drift')
    rows=[json.loads(x) for x in raw.splitlines()]
    expected=manifest['sample_count'] if stage=='sample' else manifest['row_count']
    if len(rows)!=expected or len({x['id'] for x in rows})!=expected or any(set(x)!= {'id','reason'} or not isinstance(x['reason'],str) for x in rows):raise ValueError('Invalid blinded rows')
    by_id={r['id']:r for r in rows}
    output.mkdir(parents=True,exist_ok=True)
    with (output/'writer.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        journal=output/'events.jsonl'; result=output/'verdicts.jsonl'
        contract=dict(stage=stage,model=manifest['model'],revision=manifest['revision'],prompt_sha256=sha(prompt),input_sha256=sha(raw),runner_sha256=sha(Path(__file__).read_bytes()),temperature=0,max_tokens=256,enable_thinking=False,base_url=base_url)
        contract_file=output/'contract.json'
        if contract_file.exists():
            if json.loads(contract_file.read_text())!=contract:raise ValueError('Contract drift')
        else:
            if journal.exists():raise ValueError('Journal without contract')
            atomic(contract_file,canonical(contract)+b'\n')
        prior=[json.loads(x) for x in journal.read_bytes().splitlines()] if journal.exists() else []
        done={}; states={}; responses={}; previous='0'*64
        for stored in prior:
            e=dict(stored);event_hash=e.pop('event_sha256')
            if e.pop('previous_sha256')!=previous or sha(canonical(dict(e,previous_sha256=previous)))!=event_hash:raise ValueError('Journal hash chain mismatch')
            previous=event_hash
            ident=e['id']
            if ident not in by_id:raise ValueError('Unknown prior ID')
            reason=by_id[ident]['reason'];kind=e['kind'];state=states.get(ident)
            if kind=='intent':
                req=request_for(manifest,prompt,reason)
                if state is not None or not reason.strip() or e['request']!=req or e['request_sha256']!=sha(canonical(req)):raise ValueError('Invalid prior intent')
                states[ident]='intent'
            elif kind=='response':
                if state!='intent':raise ValueError('Unmatched response')
                raw_response=base64.b64decode(e['raw_response_base64'],validate=True)
                if sha(raw_response)!=e['response_sha256'] or type(e['http_status']) is not int:raise ValueError('Raw response hash/status mismatch')
                responses[ident]=e;states[ident]='response'
            elif kind=='result':
                if e['status']=='input_missing':
                    expected_result=dict(kind='result',id=ident,status='input_missing',label=None,evidence=None)
                    if state is not None or reason.strip():raise ValueError('Invalid missing result')
                else:
                    if state!='response':raise ValueError('Unmatched result')
                    expected_result=dict(kind='result',id=ident,status='ok',**response_verdict(responses[ident],reason,manifest['model']))
                if e!=expected_result:raise ValueError('Result differs from raw response')
                states[ident]='done';done[ident]=e
            elif kind=='error':
                if state not in ('intent','response'):raise ValueError('Unmatched error')
                raise ValueError('Previous error retained; explicit review required')
            else:raise ValueError('Unknown event')
        if any(v!='done' for v in states.values()):raise ValueError('Unresolved request; do not retry')
        atomic(result,b''.join(canonical(x)+b'\n' for x in done.values()))
        def emit(row):
            nonlocal previous
            e=dict(row,previous_sha256=previous);previous=sha(canonical(e));append(journal,dict(e,event_sha256=previous))
        for row in rows:
            ident,reason=row['id'],row['reason']
            if ident in done:continue
            if not reason.strip():
                v=dict(kind='result',id=ident,status='input_missing',label=None,evidence=None)
                emit(v);append(result,v);done[ident]=v;continue
            request=request_for(manifest,prompt,reason)
            emit(dict(kind='intent',id=ident,request=request,request_sha256=sha(canonical(request))))
            start=time.monotonic()
            try:
                try:
                    with urlopen(Request(base_url.rstrip('/')+'/v1/chat/completions',data=canonical(request),headers={'Content-Type':'application/json'}),timeout=180) as reply:
                        raw_response=reply.read();http_status=getattr(reply,'status',200)
                except HTTPError as error:
                    raw_response=error.read();http_status=error.code
                event=dict(kind='response',id=ident,raw_response_base64=base64.b64encode(raw_response).decode(),response_sha256=sha(raw_response),http_status=http_status,seconds=time.monotonic()-start)
                emit(event)
                parsed=response_verdict(event,reason,manifest['model'])
                v=dict(kind='result',id=ident,status='ok',**parsed)
                emit(v);append(result,v);done[ident]=v
            except Exception as exc:
                emit(dict(kind='error',id=ident,error_type=type(exc).__name__,message=str(exc)))
                raise
            if len(done)%10==0:print(stage,len(done),'/',len(rows),flush=True)
        summary=dict(stage=stage,rows=len(rows),completed=len(done),input_missing=sum(x['status']=='input_missing' for x in done.values()),status='COLLECTED',scientific_validation=False)
        atomic(output/'summary.json',canonical(summary)+b'\n')
        return summary
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--package',type=Path,default=Path(__file__).parent);p.add_argument('--stage',choices=['sample','all'],required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--base-url',default='http://127.0.0.1:18081');a=p.parse_args()
    print(json.dumps(collect(a.package,a.stage,a.output,a.base_url)))