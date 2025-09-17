# ---------- Imports ----------
import os
from typing import List, Optional, Any, Dict
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware   # For handling Cross-Origin Resource Sharing (CORS)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

# Import internal modules (your custom logic for handling docs)
from src.document_ingestion.data_ingestion import (
    DocHandler,                # For handling document uploads
    DocumentComparator,        # For comparing documents (basic)
    ChatIngestor,              # For ingesting documents into FAISS for chat
)
from src.document_analyzer.data_analysis import DocumentAnalyzer
from src.document_compare.document_comparator import DocumentComparatorLLM
from src.document_chat.retrieval import ConversationalRAG
from utils.document_ops import FastAPIFileAdapter, read_pdf_via_handler
from logger.custom_logger import CustomLogger

# Setup structured logger
log = CustomLogger().get_logger(__name__)

# ---------- Environment defaults ----------
FAISS_BASE = os.getenv("FAISS_BASE", "faiss_index")   # Where FAISS indexes are stored
UPLOAD_BASE = os.getenv("UPLOAD_BASE", "data")        # Base folder for uploaded documents
FAISS_INDEX_NAME = os.getenv("FAISS_INDEX_NAME", "index")  # Default index name

# ---------- FastAPI app initialization ----------
app = FastAPI(title="Document Portal API", version="0.1")

# Setup static + template dirs
BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ---------- Middleware ----------
# Allow cross-origin requests (important if frontend runs on different domain/port)
# CORS is a browser security mechanism.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Allow all domains (can be restricted in prod)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Routes ----------

# Root: serves the UI (index.html)
@app.get("/", response_class=HTMLResponse)
async def serve_ui(request: Request):
    log.info("Serving UI homepage.")
    resp = templates.TemplateResponse("index.html", {"request": request})
    resp.headers["Cache-Control"] = "no-store"  # Prevent caching of homepage
    return resp

# Health check endpoint (useful for monitoring, Kubernetes probes, etc.)
@app.get("/health")
def health() -> Dict[str, str]:
    log.info("Health check passed.")
    return {"status": "ok", "service": "document-portal"}


# ---------- ANALYZE ----------
@app.post("/analyze")
async def analyze_document(file: UploadFile = File(...)) -> Any:
    """Upload one document and analyze its contents (text extraction + NLP analysis)."""
    try:
        log.info(f"Received file for analysis: {file.filename}")
        
        dh = DocHandler()  # Handles saving and reading of uploaded docs
        saved_path = dh.save_pdf(FastAPIFileAdapter(file))  # Save uploaded file
        
        text = read_pdf_via_handler(dh, saved_path)  # Extract raw text from PDF  (samajgha ye kaiku karko)
        analyzer = DocumentAnalyzer()               # Initialize analyzer
        result = analyzer.analyze_document(text)    # Run analysis
        
        log.info("Document analysis complete.")
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Error during document analysis")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


# ---------- COMPARE ----------
@app.post("/compare")
async def compare_documents(reference: UploadFile = File(...), actual: UploadFile = File(...)) -> Any:
    """Upload two documents and compare them."""
    try:
        log.info(f"Comparing files: {reference.filename} vs {actual.filename}") #Logging Info with file names
        
        # Initialize the DocumentComparator (responsible for saving + reading + merging docs)
        dc = DocumentComparator()
        ref_path, act_path = dc.save_uploaded_files(
            FastAPIFileAdapter(reference), FastAPIFileAdapter(actual)
        ) # Save both uploaded files using FastAPIFileAdapter (so they can be read like regular files)
        
        # Assign to underscore to indicate that paths are unused in later code,
        # but calling this ensures the files were actually saved
        _ = ref_path, act_path  # unused but confirms saving

        combined_text = dc.combine_documents()  # Merge extracted text
        #Note: here we are not passing files directly, rather this method picks the saved files from session_dir
        
        # Initialize the LLM-based comparator
        comp = DocumentComparatorLLM()          # Use LLM for semantic comparison
        df = comp.compare_documents(combined_text) #pass the combined text to compare_documents method

        # 🧹 cleanup: keep only 3 latest session folders
        # dc.clean_old_sessions(keep_latest=3)
        
        log.info("Document comparison completed.")
        return {"rows": df.to_dict(orient="records"), "session_id": dc.session_id}
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Comparison failed")
        raise HTTPException(status_code=500, detail=f"Comparison failed: {e}")


# # ---------- Environment defaults ---------- (same thing defied above)
# FAISS_BASE = os.getenv("FAISS_BASE", "faiss_index")   # Where FAISS indexes are stored
# UPLOAD_BASE = os.getenv("UPLOAD_BASE", "data")        # Base folder for uploaded documents
# FAISS_INDEX_NAME = os.getenv("FAISS_INDEX_NAME", "index")  # Default index name

# ---------- CHAT: INDEX ----------
@app.post("/chat/index")
async def chat_build_index(
    files: List[UploadFile] = File(...),   # Accept multiple documents uploaded by user
    session_id: Optional[str] = Form(None),  # Optional session id (name) create session with given name if given
    use_session_dirs: bool = Form(True),     # Whether to created session-specific index or to over write the current index (samajga)
    chunk_size: int = Form(1000),            # Each document will be split into chunks of this size
    chunk_overlap: int = Form(200),          # Overlap between chunks for better context continuity
    k: int = Form(5),                        # Number of top chunks to retrieve during search
) -> Any:
    """Build FAISS index from uploaded documents for conversational search."""
    try:
        # Log that we’re starting indexing, include session id and filenames
        log.info(f"Indexing chat session. Session ID: {session_id}, Files: {[f.filename for f in files]}")

        # Wrap FastAPI UploadFile objects into adapter so they expose .name & .getbuffer()
        wrapped = [FastAPIFileAdapter(f) for f in files]

        # Initialize ChatIngestor (class responsible for saving docs and building FAISS index)
        ci = ChatIngestor(
            temp_base=UPLOAD_BASE,          # Temp storage base path for uploads
            faiss_base=FAISS_BASE,          # Where FAISS vector indexes will be stored
            use_session_dirs=use_session_dirs, # Organize indexes/documents by session folders
            session_id=session_id or None,  # Either reuse given session_id or auto-generate
        )

        # Build retriever from uploaded docs → text chunks → embeddings → FAISS index
        ci.built_retriver(
            wrapped, 
            chunk_size=chunk_size,          # Size of each chunk
            chunk_overlap=chunk_overlap,    # Overlap ensures context continuity across chunks
            k=k                             # Top-k retrieval (used later in chat stage)
        )
        
        # If success, log and return metadata back to frontend
        log.info(f"Index created successfully for session: {ci.session_id}")
        return {"session_id": ci.session_id, "k": k, "use_session_dirs": use_session_dirs}

    except HTTPException:
        # If FastAPI HTTPException was raised, just re-raise it
        raise
    except Exception as e:
        # Catch unexpected errors, log full traceback and return HTTP 500
        log.exception("Chat index building failed")
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")



# ---------- CHAT: QUERY ----------
@app.post("/chat/query")
async def chat_query(
    question: str = Form(...),                       # user query from frontend
    session_id: Optional[str] = Form(None),          # session ID to pick correct FAISS index
    use_session_dirs: bool = Form(True),             # whether to use session-specific FAISS dirs
    k: int = Form(5),                                # how many chunks to retrieve (top-k)
) -> Any:
    """Query previously indexed documents (RAG pipeline)."""
    try:
        log.info(f"Received chat query: '{question}' | session: {session_id}")
        
        # --- 1️⃣ Validation ---
        if use_session_dirs and not session_id:
            # If working in session mode but no session_id provided → error
            raise HTTPException(status_code=400, detail="session_id is required when use_session_dirs=True")

        # --- 2️⃣ Locate the FAISS index directory ---
        index_dir = os.path.join(FAISS_BASE, session_id) if use_session_dirs else FAISS_BASE
        if not os.path.isdir(index_dir):
            # If the directory doesn’t exist → no index was built yet
            raise HTTPException(status_code=404, detail=f"FAISS index not found at: {index_dir}")

        # --- 3️⃣ Initialize Conversational RAG ---
        rag = ConversationalRAG(session_id=session_id)  # Create RAG engine tied to this session
        rag.load_retriever_from_faiss(
            index_dir, 
            k=k, 
            index_name=FAISS_INDEX_NAME                # loads FAISS retriever with top-k setup
        )
        
        # --- 4️⃣ Run user question through retriever + LLM ---
        response = rag.invoke(
            question, 
            chat_history=[]   # currently no memory → stateless queries
        )
        
        # --- 5️⃣ Return the answer ---
        log.info("Chat query handled successfully.")
        return {
            "answer": response,       # final LLM response
            "session_id": session_id, # session used for retrieval
            "k": k,                   # retrieval depth
            "engine": "LCEL-RAG"      # engine identifier
        }
    
    except HTTPException:
        raise   # rethrow FastAPI-level HTTP errors
    
    except Exception as e:
        # Any other runtime error
        log.exception("Chat query failed")
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")



# ---------- Run Instructions ----------
# To start server locally:
# uvicorn api.main:app --port 8080 --reload    
# or for cloud:
# uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload