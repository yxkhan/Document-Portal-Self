from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware  # For handling Cross-Origin Resource Sharing (CORS)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from typing import List, Optional, Any, Dict

app = FastAPI(title="Documnet Portal API", version="0.1")

from src.document_ingestion.data_ingestion import (
    DocHandler,
    DocumnetComparator,
    ChatIngestor,
    FaissManager
)

from src.document_analyzer.data_analysis import DocumentAnalyzer
from src.document_compare.document_comparator import DocumentComparatorLLM
from src.document_chat.retrieval import ConversationalRAG

#This is for cloud to make the authentication of the keys and other factors
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


class FastAPIFileAdapter:
    """Adapt FastAPI UploadFile -> .name + .getbuffer() API"""
    def __init__(self, uf: UploadFile):
        self._uf = uf
        self.name = uf.filename
    def getbuffer(self) -> bytes:
        self._uf.file.seek(0)
        return self._uf.file.read()

def _read_pdf_via_handler(handler: DocHandler, path:str) -> str:
    """
    Helper function to read PDF using DocHandler.
    """
    try:
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading PDF: {str(e)}")

#complete logic for the document analysis 
@app.post("/analyze")   #Route to document analysis page
async def analyze_document(file: UploadFile = File(...)) -> Any: #along with that route this method is appended
    try:

        dh = DocHandler() #creaing an instance
        saved_path = dh.save_pdf(FastAPIFileAdapter(file)) #saving the file with FastAPIFileAdapter
        text = _read_pdf_via_handler(dh, saved_path)

        analyzer=DocumentAnalyzer()
        result = analyzer.analyze_document(text)
        return JSONResponse(content=result) #returning the result as json response and as content
    
    except HTTPException:   #Note: here we dont call the custom exception because fastapi has its own exception handling mechanism
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    
#complete logic for the document compare 
@app.post("/compare")
async def compare_documents(reference: UploadFile = File(...), actual: UploadFile = File(...)) -> Any:
    try:

        dc = DocumnetComparator()
        ref_path, act_path = dc.save_uploaded_files(FastAPIFileAdapter(reference), FastAPIFileAdapter(actual))
        _ = ref_path, act_path   #i think its for session id
        combined_text = dc.combine_documents()
        comp = DocumentComparatorLLM()
        df = comp.compare_documents(combined_text)
        return {"rows": df.to_dict(orient="records"), "session_id": dc.session_id}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {e}")

#complete logic for the document load chat
@app.post("/chat/index")
# async def chat_build_index() -> Any:
async def chat_build_index(
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Form(None),
    use_session_dirs: bool = Form(True),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200),
    k: int = Form(5),
) -> Any:   #These all the details we are getting from the UI itself
    try:

        wrapped = [FastAPIFileAdapter(f) for f in files] #wrapping all the files
        ci = ChatIngestor(
            temp_base=UPLOAD_BASE,
            faiss_base=FAISS_BASE,
            use_session_dirs=use_session_dirs,
            session_id=session_id or None,
        ) #creating the instance of ChatIngestor class
        ci.build_retriever(wrapped, chunk_size=chunk_size, chunk_overlap=chunk_overlap, k=k) #calling the build_ret
        return {"session_id": ci.session_id, "k": k, "use_session_dirs": use_session_dirs}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")
    
#complete logic for the document chat query
@app.post("/chat/query")
async def chat_query(
    question: str = Form(...),
    session_id: Optional[str] = Form(None),
    use_session_dirs: bool = Form(True),
    k: int = Form(5),
) -> Any:
    
    try:

        if use_session_dirs and not session_id:
            raise HTTPException(status_code=400, detail="session_id is required when use_session_dirs=True")

        # Prepare FAISS index path
        index_dir = os.path.join(FAISS_BASE, session_id) if use_session_dirs else FAISS_BASE  # type: ignore
        if not os.path.isdir(index_dir):
            raise HTTPException(status_code=404, detail=f"FAISS index not found at: {index_dir}")

        # Initialize LCEL-style RAG pipeline
        rag = ConversationalRAG(session_id=session_id) #type: ignore
        rag.load_retriever_from_faiss(index_dir)

        # Optional: For now we pass empty chat history
        response = rag.invoke(question, chat_history=[])

        return {
            "answer": response,
            "session_id": session_id,
            "k": k,
            "engine": "LCEL-RAG"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")


# command for executing the fast api
#Please note: change directory to api folder before running the below command
# uvicorn api.main:app --reload
#Code is working smooth