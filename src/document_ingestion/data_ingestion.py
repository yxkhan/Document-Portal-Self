#One data ingestion class to handle all the data ingestion related tasks

from __future__ import annotations #For forward compatibility
import os
import sys
import json
import uuid
import hashlib
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Iterable, List, Optional, Dict, Any

import fitz  # PyMuPDF
from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_community.vectorstores import FAISS

from utils.model_loader import ModelLoader
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException

from utils.file_io import _session_id, save_uploaded_files
from utils.document_ops import load_documents, concat_for_analysis, concat_for_comparison

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}

# FAISS Manager (load-or-create)
class FaissManager:
    def __init__(self, index_dir: Path, model_loader: Optional[ModelLoader] = None):
        self.index_dir = Path(index_dir)
        #create a index directory
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        #Metapath to keep the metadata
        # Path where we will save metadata about ingested documents.
        # (This JSON file will sit next to the FAISS index)
        self.meta_path = self.index_dir / "ingested_meta.json" #To load the data like (using what files this particular session is created)
        # Dictionary to keep track of all files we added into FAISS.
        # - "rows" is like a table of records
        # - Each record stores info like file name, chunks, timestamp, etc.
        # - Useful to know: what files are in FAISS, when they were added
        self._meta: Dict[str, Any] = {"rows": {}}   #this is dict of rows to keep the track of the data
        
        #validate the metapath
        if self.meta_path.exists():
            try:
                self._meta = json.loads(self.meta_path.read_text(encoding="utf-8")) or {"rows": {}}  #load it if its already there
            except Exception:
                self._meta = {"rows": {}} #if the metapath doesn't exist assign/initialise it like this
        
        #define the model loaders
        self.model_loader = model_loader or ModelLoader()
        self.emb = self.model_loader.load_embeddings()
        self.vs: Optional[FAISS] = None  #to capture the faiss vdb
        
    def _exists(self)-> bool:
        """to check the faiss index and ,pkl exist or not just gives True or False"""
        return (self.index_dir / "index.faiss").exists() and (self.index_dir / "index.pkl").exists()
    
    @staticmethod
    def _fingerprint(text: str, md: Dict[str, Any]) -> str:  #This function is to remove the de-duplicates
        src = md.get("source") or md.get("file_path") #md means metadata
        rid = md.get("row_id")
        if src is not None:
            return f"{src}::{'' if rid is None else rid}" #To check if there any duplicates in the data using metadata
        return hashlib.sha256(text.encode("utf-8")).hexdigest() #using sha256 algorithm to create a unique hash value for the new data
    
    def _save_meta(self):
        self.meta_path.write_text(json.dumps(self._meta, ensure_ascii=False, indent=2), encoding="utf-8") #To save metadata
    

    def add_documents(self, docs: List[Document]):
        """Add new documents into FAISS (avoiding duplicates) and update metadata."""

        # First check: Did we already load/create a FAISS index?
        if self.vs is None:
            raise RuntimeError("Call load_or_create() before add_documents().")

        new_docs: List[Document] = []

        for d in docs:
            # Create a unique fingerprint for the doc (based on text + metadata).
            key = self._fingerprint(d.page_content, d.metadata or {})

            # If fingerprint already exists in metadata → it's a duplicate, skip it.
            if key in self._meta["rows"]:
                continue  

            # Otherwise → mark it in metadata and keep it for adding.
            self._meta["rows"][key] = True
            new_docs.append(d)

        # Only if we actually have new docs to add:
        if new_docs:
            # Add them to FAISS index
            self.vs.add_documents(new_docs)
            # Save FAISS index to disk
            self.vs.save_local(str(self.index_dir))
            # Save updated metadata JSON to disk
            self._save_meta()

        # Return how many NEW docs were added (0 if everything was duplicate)
        return len(new_docs)

    
    def load_or_create(self, texts: Optional[List[str]] = None, metadatas: Optional[List[dict]] = None):
        """Load existing FAISS index if available, otherwise create a new one from scratch."""

        # Case 1: If FAISS index already exists on disk → just load it.
        if self._exists():
            self.vs = FAISS.load_local(
                str(self.index_dir),
                embeddings=self.emb,
                allow_dangerous_deserialization=True,  # allows pickle (safe here because it's our own index)
            )
            return self.vs

        # Case 2: If index doesn't exist AND no texts were given → we cannot create anything.
        if not texts:
            raise DocumentPortalException("No existing FAISS index and no data to create one", sys)

        # Case 3: If no index exists but texts are provided → create new FAISS index from scratch.
        self.vs = FAISS.from_texts(texts=texts, embedding=self.emb, metadatas=metadatas or [])
        self.vs.save_local(str(self.index_dir))
        return self.vs



class ChatIngestor:
    def __init__( self,
        temp_base: str = "data",             # Base folder for temporarily saving uploaded documents
        faiss_base: str = "faiss_index",     # Base folder for storing FAISS vector indexes
        use_session_dirs: bool = True,       # Whether to create separate directories/index per session or over ride the existing one 
        session_id: Optional[str] = None,    # Custom session ID (if not provided, auto-generate)
    ):
        try:
            self.log = CustomLogger().get_logger(__name__)  # Setup custom logger
            self.model_loader = ModelLoader()               # Loader for embeddings + LLMs
            
            self.use_session = use_session_dirs             # Save whether session dirs should be used
            self.session_id = session_id or _session_id()   # Use given session_id or generate a new one which will be created from file_io.py
            
            # ---------- DATA VERSIONING ----------
            self.temp_base = Path(temp_base); self.temp_base.mkdir(parents=True, exist_ok=True)  
            # Ensure "data/" folder exists → stores uploaded raw documents
            
            self.faiss_base = Path(faiss_base); self.faiss_base.mkdir(parents=True, exist_ok=True)  
            # Ensure "faiss_index/" folder exists → stores FAISS indexes
            
            # ---------- SESSION HANDLING ----------
            self.temp_dir = self._resolve_dir(self.temp_base)    # Create/find session folder inside "data/"
            self.faiss_dir = self._resolve_dir(self.faiss_base)  # Create/find session folder inside "faiss_index/"
            
            # ---------- LOGGING ----------
            self.log.info("ChatIngestor initialized",
                          session_id=self.session_id,
                          temp_dir=str(self.temp_dir),
                          faiss_dir=str(self.faiss_dir),
                          sessionized=self.use_session)
        except Exception as e:
            self.log.error("Failed to initialize ChatIngestor", error=str(e))
            raise DocumentPortalException("Initialization error in ChatIngestor", e) from e
    
    
    def _resolve_dir(self, base: Path):   #whether to create separate session directory or to over write the existing one
        if self.use_session:
            d = base / self.session_id          # Create a session-specific subfolder (e.g. data/<session_id>)
            d.mkdir(parents=True, exist_ok=True)
            return d
        return base                             # If sessioning disabled → just return base folder directly
    
    
    def _split(self, docs: List[Document], chunk_size=1000, chunk_overlap=200) -> List[Document]:
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)  
        # Split docs into smaller overlapping chunks → required for embedding + retrieval
        
        chunks = splitter.split_documents(docs)
        self.log.info("Documents split", chunks=len(chunks), chunk_size=chunk_size, overlap=chunk_overlap)
        return chunks
    
    
    def built_retriver( self,
        uploaded_files: Iterable,
        *,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        k: int = 5,):
        try:
            paths = save_uploaded_files(uploaded_files, self.temp_dir)   # Save uploaded files to session folder
            docs = load_documents(paths)                                 # Load documents into LangChain format
            if not docs:
                raise ValueError("No valid documents loaded")            # Raise error if nothing loaded
            
            chunks = self._split(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)  
            # Split docs into smaller chunks
            
            # ---------- FAISS INDEXING ----------
            fm = FaissManager(self.faiss_dir, self.model_loader)         # Manager for FAISS index
            
            texts = [c.page_content for c in chunks]                     # Extract text content from chunks
            metas = [c.metadata for c in chunks]                         # Extract metadata from chunks
            
            try:
                vs = fm.load_or_create(texts=texts, metadatas=metas)     # Either load existing index OR create new
            except Exception:
                vs = fm.load_or_create(texts=texts, metadatas=metas)     # Retry if first attempt fails
                
            added = fm.add_documents(chunks)                             # Add new docs to FAISS index
            self.log.info("FAISS index updated", added=added, index=str(self.faiss_dir))
            
            # Return a retriever object → can fetch top-k most similar chunks
            return vs.as_retriever(search_type="similarity", search_kwargs={"k": k})
            
        except Exception as e:
            self.log.error("Failed to build retriever", error=str(e))
            raise DocumentPortalException("Failed to build retriever", e) from e



class DocHandler:
    """
    PDF save + read (page-wise) for analysis.
    """
    def __init__(self, data_dir: Optional[str] = None, session_id: Optional[str] = None):
        self.log = CustomLogger().get_logger(__name__)

        #This block from here
                # --- Session Directory Setup ---
        # Set the base data directory where documents will be stored
        # Priority:
        #   1. use the passed `data_dir` if given
        #   2. otherwise, check the environment variable "DATA_STORAGE_PATH"
        #   3. otherwise, fall back to a default path: <cwd>/data/document_analysis
        self.data_dir = data_dir or os.getenv("DATA_STORAGE_PATH", os.path.join(os.getcwd(), "data", "document_analysis"))

                # Generate or reuse a session ID
        #   - If a session_id is provided, use it
        #   - Otherwise, call `_session_id("session")` to generate a unique ID
        self.session_id = session_id or _session_id("session")

        
        # Full path for this session → e.g., <data_dir>/<session_id>
        # Each session gets its own folder to store files
        self.session_path = os.path.join(self.data_dir, self.session_id)

        os.makedirs(self.session_path, exist_ok=True) #reate the session directory (if it doesn’t already exist)
        #To here it will create a session directory to store the uploaded file
        self.log.info("DocHandler initialized", session_id=self.session_id, session_path=self.session_path)

    def save_pdf(self, uploaded_file) -> str:
        """
        Save an uploaded PDF file into the session directory.
        Returns the saved file's path.
        """
        try:
            filename = os.path.basename(uploaded_file.name)
            if not filename.lower().endswith(".pdf"):
                raise ValueError("Invalid file type. Only PDFs are allowed.")
            
            # Build the save path → e.g., <session_path>/report.pdf
            save_path = os.path.join(self.session_path, filename)
            
            # Open the destination file in write-binary mode
            with open(save_path, "wb") as f:
                # Two possibilities depending on the object type:
                if hasattr(uploaded_file, "read"):
                    # Case 1: The object has a .read() method (like FastAPI's UploadFile)
                    f.write(uploaded_file.read())
                else:
                    # Case 2: The object supports .getbuffer() (like our FastAPIFileAdapter) #Fallback refer to FastAPIFileAdapter class
                    f.write(uploaded_file.getbuffer())
            #Till here it saves the uploaded file in that session directory

            self.log.info("PDF saved successfully", file=filename, save_path=save_path, session_id=self.session_id)
            return save_path #Returns path of the session directory where our file is saves
        except Exception as e:
            self.log.error("Failed to save PDF", error=str(e), session_id=self.session_id)
            raise DocumentPortalException(f"Failed to save PDF: {str(e)}", e) from e


    def read_pdf(self, pdf_path: str) -> str:
        try:
            text_chunks = []  
            # Initialize an empty list to store text extracted from each page of the PDF.

            with fitz.open(pdf_path) as doc:  
                # Open the PDF file using PyMuPDF (fitz).
                # `doc` represents the PDF document object.
                for page_num in range(doc.page_count):  
                    # Loop through every page in the PDF by its index (0 → last page).
                    page = doc.load_page(page_num)  
                    # Load the current page object from the PDF.
                    text_chunks.append(
                        f"\n--- Page {page_num + 1} ---\n{page.get_text()}"  # type: ignore
                    )
                    # Extract text from the current page using `page.get_text()`.
                    # Add a header like "--- Page 1 ---" before the actual text.
                    # Append this to the `text_chunks` list.
            text = "\n".join(text_chunks)  
            # Combine all page texts into one big string, separated by newlines.
            self.log.info(
                "PDF read successfully", 
                pdf_path=pdf_path, 
                session_id=self.session_id, 
                pages=len(text_chunks)
            )
            # Log a success message with extra context: PDF path, session ID, and page count.
            return text  
            # Return the final combined text from the PDF.

        except Exception as e:
            self.log.error("Failed to read PDF", error=str(e), pdf_path=pdf_path, session_id=self.session_id)
            # If something goes wrong, log an error with the exception details.
            raise DocumentPortalException(f"Could not process PDF: {pdf_path}", e) from e
            # Raise a custom exception (`DocumentPortalException`) to handle errors gracefully.

        
    #Enhanced read_pdf method with OCR fallback (if pdf pages are in the form of images)
    # def read_pdf(self, pdf_path: str) -> str:
    #     try:
    #         text_chunks = []

    #         # Step 1: Try normal text extraction
    #         with fitz.open(pdf_path) as doc:
    #             for page_num in range(doc.page_count):
    #                 page = doc.load_page(page_num)
    #                 page_text = page.get_text("text")  # explicitly ask for text
    #                 if page_text.strip():
    #                     text_chunks.append(f"\n--- Page {page_num + 1} ---\n{page_text}")

    #         # Step 2: If still no text → fall back to OCR
    #         if not any(text_chunks):
    #             self.log.warning("No text found with PyMuPDF, falling back to OCR...", pdf_path=pdf_path)
    #             images = convert_from_path(pdf_path)
    #             for i, image in enumerate(images):
    #                 page_text = pytesseract.image_to_string(image)
    #                 text_chunks.append(f"\n--- OCR Page {i+1} ---\n{page_text}")

    #         text = "\n".join(text_chunks)
    #         self.log.info(
    #             "PDF read successfully",
    #             pdf_path=pdf_path,
    #             session_id=self.session_id,
    #             pages=len(text_chunks),
    #         )
    #         return text

        # except Exception as e:
        #     self.log.error("Failed to read PDF", error=str(e), pdf_path=pdf_path, session_id=self.session_id)
        #     raise DocumentPortalException(f"Could not process PDF: {pdf_path}", e) from e



class DocumentComparator:
    """
    Save, read & combine PDFs for comparison with session-based versioning.
    """

    def __init__(self, base_dir: str = "data/document_compare", session_id: Optional[str] = None):
        self.log = CustomLogger().get_logger(__name__)   # Create a logger for this class
        self.base_dir = Path(base_dir)                   # Base directory where session folders will be stored
        self.session_id = session_id or _session_id()    # Use provided session_id or generate a new one
        self.session_path = self.base_dir / self.session_id   # Path of current session directory
        self.session_path.mkdir(parents=True, exist_ok=True)  # Create session folder (with parent dirs if needed)
        self.log.info("DocumentComparator initialized", session_path=str(self.session_path))  # Log init details

    def save_uploaded_files(self, reference_file, actual_file):
        """Save the uploaded reference and actual PDF files into session directory"""
        try:
            ref_path = self.session_path / reference_file.name   # Path for reference PDF
            act_path = self.session_path / actual_file.name      # Path for actual PDF
            
            # Loop over both files (reference + actual) and save them
            for fobj, out in ((reference_file, ref_path), (actual_file, act_path)):
            # Loop over two pairs of (file_object, output_path):
            #   1. (reference_file, ref_path) → handles the reference PDF
            #   2. (actual_file, act_path)    → handles the actual PDF
            # In each iteration:
            #   - `fobj` will be the file object (reference_file or actual_file)
            #   - `out` will be the corresponding save location (ref_path or act_path)
            # Python allows tuple unpacking directly in a for loop.

                if not fobj.name.lower().endswith(".pdf"):       # Ensure file is a PDF
                    raise ValueError("Only PDF files are allowed.")
                with open(out, "wb") as f:                       # Open file in binary write mode
                    if hasattr(fobj, "read"):                    # If object has a read() method (like UploadFile)
                        f.write(fobj.read())                     # Save content directly
                    else:                                        # Otherwise, use getbuffer() (like FastAPIFileAdapter)
                        f.write(fobj.getbuffer())
            
            # Log success with file paths
            self.log.info("Files saved", reference=str(ref_path), actual=str(act_path), session=self.session_id)
            return ref_path, act_path   # Return both saved file paths
        except Exception as e:
            # Log error and raise custom exception
            self.log.error("Error saving PDF files", error=str(e), session=self.session_id)
            raise DocumentPortalException("Error saving files", e) from e

    def read_pdf(self, pdf_path: Path) -> str:
        """Read text from a single PDF file, page by page"""
        try:
            with fitz.open(pdf_path) as doc:                     # Open PDF with PyMuPDF
                if doc.is_encrypted:                             # Check if PDF is password protected
                    raise ValueError(f"PDF is encrypted: {pdf_path.name}")
                parts = []                                       # Collect text page by page
                for page_num in range(doc.page_count):           # Loop through all pages
                    page = doc.load_page(page_num)               # Load each page
                    text = page.get_text()                       # Extract text from page
                    if text.strip():                             # Only add if text is not empty
                        parts.append(f"\n --- Page {page_num + 1} --- \n{text}")
            # Log reading success
            self.log.info("PDF read successfully", file=str(pdf_path), pages=len(parts))
            return "\n".join(parts)                              # Return full text with page markers
        except Exception as e:
            # Log error and raise custom exception
            self.log.error("Error reading PDF", file=str(pdf_path), error=str(e))
            raise DocumentPortalException("Error reading PDF", e) from e

    def combine_documents(self) -> str:
        """Combine text from all PDFs in the session directory"""
        try:
            doc_parts = []                                       # Store text of all PDFs
            for file in sorted(self.session_path.iterdir()):     # Loop through files in session dir
                if file.is_file() and file.suffix.lower() == ".pdf":   # Only process PDFs
                    content = self.read_pdf(file)                # Read text of PDF using read_pdf() method
                    doc_parts.append(f"Document: {file.name}\n{content}") # Tag with filename
            combined_text = "\n\n".join(doc_parts)               # Combine all documents into one string
            self.log.info("Documents combined", count=len(doc_parts), session=self.session_id)
            return combined_text                                 # Return merged text
        except Exception as e:
            self.log.error("Error combining documents", error=str(e), session=self.session_id)
            raise DocumentPortalException("Error combining documents", e) from e

    def clean_old_sessions(self, keep_latest: int = 3):
        """Keep only the latest N session folders, delete older ones"""
        try:
            # Get all session directories sorted (latest first)
            sessions = sorted([f for f in self.base_dir.iterdir() if f.is_dir()], reverse=True)
            for folder in sessions[keep_latest:]:                # Delete older sessions beyond `keep_latest`
                shutil.rmtree(folder, ignore_errors=True)        # Remove folder & its contents
                self.log.info("Old session folder deleted", path=str(folder))
        except Exception as e:
            self.log.error("Error cleaning old sessions", error=str(e))
            raise DocumentPortalException("Error cleaning old sessions", e) from e


