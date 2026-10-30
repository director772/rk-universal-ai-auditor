from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path
app = FastAPI(title='RK Universal AI Auditor V3', version='0.3.0')
ROOT=Path(__file__).resolve().parents[1]
@app.get('/')
def home(): return FileResponse(ROOT/'public'/'index.html')
@app.get('/health')
def health(): return {'status':'ok','version':'0.3.0','mode':'read-only snapshot prototype','live_connectors':False,'audit_history':False}
