from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware  # For handling Cross-Origin Resource Sharing (CORS)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from typing import List, Optional, Any, Dict

app = FastAPI(title="Documnet Portal API", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# serve static & templates (.css and .html files)
app.mount("/static", StaticFiles(directory="../static"), name="static")
templates = Jinja2Templates(directory="../templates")

#This would also be our Homepage/entry-point for our application
@app.get("/",response_class=HTMLResponse)  #root path pe jab bhi request aayegi ye function call hoga
async def serve_ui(request: Request):
    # templates/index.html ko render karega
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")  #To check our response and request working fine or not
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "document-portal"}

#complete logic for the document analysis 
@app.post("/analyze")   #To analyze the document
async def analyze_document(file: UploadFile = File(...)) -> Any:
    try:
        pass
    except HTTPException:   #Note: here we dont call the custom exception because fastapi has its own exception handling mechanism
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    
#complete logic for the document compare 
@app.post("/compare")
async def compare_documents(reference: UploadFile = File(...), actual: UploadFile = File(...)) -> Any:
    try:
        pass
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {e}")

#complete logic for the document load chat
@app.post("/chat/index")
async def chat_build_index() -> Any:
    try:
        pass
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")
    
#complete logic for the document chat query
@app.post("/chat/query")
async def chat_query():
    try:
        pass
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")


# command for executing the fast api
#Please note: change directory to api folder before running the below command
# uvicorn api.main:app --reload