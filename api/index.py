import json, os, uuid, re
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATABASE_URL=os.getenv('DATABASE_URL', 'sqlite:///'+str(ROOT/'auditor_local.db'))
if DATABASE_URL.startswith('postgres://'): DATABASE_URL=DATABASE_URL.replace('postgres://','postgresql+psycopg://',1)
if DATABASE_URL.startswith('postgresql://'): DATABASE_URL=DATABASE_URL.replace('postgresql://','postgresql+psycopg://',1)
engine=create_engine(DATABASE_URL, pool_pre_ping=True)
app=FastAPI(title='RK Universal AI Auditor',version='0.2.0')
SCOPES={'crm':['Leads & Duplicates','Status & Assignment','Missing Records'], 'websheet':['Leads & Duplicates','Status & Assignment','Missing Records'], 'web':['Page Availability (requires connector)','Permissions (requires connector)'], 'accounting':['Ledger Reconciliation (requires connector)','Vendor Settlements (requires connector)'], 'operation':['Document Reconciliation (requires connector)']}

def now(): return datetime.now(timezone.utc).isoformat()

def setup():
    with engine.begin() as c:
        c.execute(text('CREATE TABLE IF NOT EXISTS systems (id VARCHAR(40) PRIMARY KEY, name VARCHAR(150) NOT NULL, kind VARCHAR(40) NOT NULL, url TEXT NOT NULL, scopes TEXT NOT NULL, created_at VARCHAR(50) NOT NULL)'))
        c.execute(text('CREATE TABLE IF NOT EXISTS runs (id VARCHAR(40) PRIMARY KEY, system_id VARCHAR(40) NOT NULL, scopes TEXT NOT NULL, created_at VARCHAR(50) NOT NULL, findings TEXT NOT NULL, summary TEXT NOT NULL)'))
setup()

def auth(x_api_key):
    secret=os.getenv('AUDITOR_API_KEY')
    if not secret: raise HTTPException(503,'AUDITOR_API_KEY environment variable missing')
    import hmac
    if not x_api_key or not hmac.compare_digest(x_api_key,secret): raise HTTPException(401,'Invalid API key')

def system_row(r):
    d=dict(r); d['scopes']=json.loads(d['scopes']); return d

class NewSystem(BaseModel):
    name:str=Field(min_length=2,max_length=150)
    kind:str=Field(pattern='^(crm|websheet|web|accounting|operation)$')
    url:str=Field(default='',max_length=1000)

class Lead(BaseModel):
    lead_id:str=Field(min_length=1,max_length=150)
    phone:str=''
    status:str=''
    assigned_to:str=''

class AuditRequest(BaseModel):
    system_id:str
    scopes:list[str]=Field(min_length=1)
    app_leads:list[Lead]=Field(default_factory=list,max_length=10000)
    sheet_leads:list[Lead]=Field(default_factory=list,max_length=10000)

@app.get('/')
def home(): return FileResponse(ROOT/'public'/'index.html')

@app.get('/health')
def health(): return {'status':'ok','service':'rk-auditor','version':'0.2.0','database_configured':bool(os.getenv('DATABASE_URL'))}

@app.get('/api/systems')
def list_systems(x_api_key:Optional[str]=Header(None)):
    auth(x_api_key)
    with engine.connect() as c:
        return {'systems':[system_row(r) for r in c.execute(text('SELECT * FROM systems ORDER BY created_at DESC')).mappings()]}

@app.post('/api/systems')
def add_system(data:NewSystem,x_api_key:Optional[str]=Header(None)):
    auth(x_api_key)
    if data.url and not re.match(r'^https://[^\s]+$', data.url): raise HTTPException(422,'Use an HTTPS URL, or leave it empty')
    system={'id':str(uuid.uuid4()),'name':data.name.strip(),'kind':data.kind,'url':data.url,'scopes':SCOPES[data.kind],'created_at':now()}
    with engine.begin() as c:
        c.execute(text('INSERT INTO systems (id,name,kind,url,scopes,created_at) VALUES (:id,:name,:kind,:url,:scopes,:created_at)'),{**system,'scopes':json.dumps(system['scopes'])})
    return {'system':system}

@app.post('/api/audits')
def run_audit(data:AuditRequest,x_api_key:Optional[str]=Header(None)):
    auth(x_api_key)
    with engine.connect() as c:
        row=c.execute(text('SELECT * FROM systems WHERE id=:id'),{'id':data.system_id}).mappings().first()
    if not row: raise HTTPException(404,'System not found')
    system=system_row(row)
    if not set(data.scopes).issubset(set(system['scopes'])): raise HTTPException(422,'Unknown audit scope')
    if system['kind'] not in ('crm','websheet'): raise HTTPException(409,'This system needs a read-only connector before a real audit can run')
    if not data.app_leads and not data.sheet_leads: raise HTTPException(422,'Provide actual app and sheet snapshots; no live connector is configured')
    a={}; s={}
    for record in data.app_leads:a.setdefault(record.lead_id,[]).append(record)
    for record in data.sheet_leads:s.setdefault(record.lead_id,[]).append(record)
    findings=[]
    def add(rule,priority,evidence):findings.append({'id':str(uuid.uuid4()),'rule':rule,'priority':priority,'classification':'Mismatch Found — Needs Verification','evidence':evidence})
    if 'Leads & Duplicates' in data.scopes:
        for source,items in [('app',a),('sheet',s)]:
            for lid,rows in items.items():
                if len(rows)>1:add('Duplicate lead ID','high',{'source':source,'lead_id':lid,'count':len(rows)})
    if 'Missing Records' in data.scopes:
        for lid in sorted(set(a)^set(s)):
            add('Missing record','high',{'lead_id':lid,'missing_from':'sheet' if lid in a else 'app'})
    if 'Status & Assignment' in data.scopes:
        for lid in sorted(set(a)&set(s)):
            if len(a[lid])!=1 or len(s[lid])!=1:continue
            for field in ('phone','status','assigned_to'):
                x=getattr(a[lid][0],field);y=getattr(s[lid][0],field)
                if x!=y:add('Field mismatch','high',{'lead_id':lid,'field':field,'app':x,'sheet':y})
    rid=str(uuid.uuid4());stamp=now()
    report={'id':rid,'system_id':system['id'],'system':system['name'],'scopes':data.scopes,'created_at':stamp,'findings':findings,'summary':f'{len(findings)} potential findings; {len(data.app_leads)} app and {len(data.sheet_leads)} sheet snapshot records','limitations':['User-provided snapshots only','No live web app/browser testing','Source differences are not automatically confirmed mistakes']}
    with engine.begin() as c:
        c.execute(text('INSERT INTO runs (id,system_id,scopes,created_at,findings,summary) VALUES (:id,:system_id,:scopes,:created_at,:findings,:summary)'),{'id':rid,'system_id':system['id'],'scopes':json.dumps(data.scopes),'created_at':stamp,'findings':json.dumps(findings),'summary':report['summary']})
    return report

@app.get('/api/audits')
def history(x_api_key:Optional[str]=Header(None)):
    auth(x_api_key)
    with engine.connect() as c: rows=c.execute(text('SELECT * FROM runs ORDER BY created_at DESC LIMIT 50')).mappings().all()
    return {'runs':[{'id':r['id'],'system_id':r['system_id'],'created_at':r['created_at'],'summary':r['summary'],'scopes':json.loads(r['scopes']),'findings':json.loads(r['findings'])} for r in rows]}
