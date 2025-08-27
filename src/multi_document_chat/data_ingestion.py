# class DocumentIngestor:
#     def __init__(self):
#         pass
    
#     def ingest_files(self):
#         pass
    
#     def _create_retriever(self, documents):
#         pass
    
import uuid
from pathlib import Path
import sys
from datetime import datetime, timezone
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from utils.model_loader import ModelLoader


class DocumentIngestor:
    SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.md'}   #mainting the dict variable of supported extensions
    def __init__(self, temp_dir:str = "data/multi_doc_chat",faiss_dir: str = "faiss_index", session_id: str | None = None):
        try:
            self.log = CustomLogger().get_logger(__name__)
            
            
            # base dirs
            self.temp_dir = Path(temp_dir)
            self.faiss_dir = Path(faiss_dir)
            self.temp_dir.mkdir(parents=True, exist_ok=True) #mkdir- make directory, parents=True- create parent directories if they don't exist, exist_ok=True- don't raise an error if the directory already exists
            self.faiss_dir.mkdir(parents=True, exist_ok=True) #mkdir- make directory, parents=True- create parent directories if they don't exist, exist_ok=True- don't raise an error if the directory already exists
            
            # sessionized paths
            self.session_id = session_id or f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            self.session_temp_dir = self.temp_dir / self.session_id #for every run will create a session folder inside temp_dir for data
            self.session_faiss_dir = self.faiss_dir / self.session_id #for every run will create a session folder inside faiss_dir for index
            self.session_temp_dir.mkdir(parents=True, exist_ok=True)
            self.session_faiss_dir.mkdir(parents=True, exist_ok=True)
            
            self.model_loader = ModelLoader()
            self.log.info(
                "DocumentIngestor initialized",
                temp_base=str(self.temp_dir),
                faiss_base=str(self.faiss_dir),
                session_id=self.session_id,
                temp_path=str(self.session_temp_dir),
                faiss_path=str(self.session_faiss_dir),
            )
        except Exception as e:
            self.log.error("Failed to initialize DocumentIngestor", error=str(e))
            raise DocumentPortalException("Initialization error in DocumentIngestor", sys)
            

    def ingest_files(self,uploaded_files):
        try:
            documents=[]
            
            for uploaded_file in uploaded_files:
                ext = Path(uploaded_file.name).suffix.lower()  #To check the name and extension of the file
                if ext not in self.SUPPORTED_EXTENSIONS:       #That why we have defined that dict
                    self.log.warning("Unsupported file skipped", filename=uploaded_file.name)  #Just raise the warning and
                    continue
                unique_filename = f"{uuid.uuid4().hex[:8]}{ext}"   #Unique name for every file for versioning purpose
                temp_path = self.session_temp_dir / unique_filename #Path to save the file
                
                with open(temp_path, "wb") as f:   #open the file in write binary mode
                    f.write(uploaded_file.read())  #write the file content to the temp_path
                self.log.info("File saved for ingestion", filename=uploaded_file.name, saved_as=str(temp_path), session_id=self.session_id) #log this info
                
                if ext == ".pdf":
                    loader = PyPDFLoader(str(temp_path)) #if ext is pdf load the data using PyPDFLoader
                elif ext == ".docx":
                    loader = Docx2txtLoader(str(temp_path))   #if ext is docx load the data using Docx2txtLoader
                elif ext == ".txt":
                    loader = TextLoader(str(temp_path), encoding="utf-8")  #if ext is txt load the data using TextLoader
                elif ext == ".md":
                    loader = TextLoader(str(temp_path), encoding="utf-8")  #if ext is md load the data using TextLoader
                else:
                    self.log.warning("Unsupported file type encountered", filename=uploaded_file.name) #Just raise the warning and
                    continue
                
                docs = loader.load()  #load the document using the loader defined above
                documents.extend(docs)  #extend the documents list with the loaded docs
                
            if not documents:
                raise DocumentPortalException("No valid documents loaded", sys) #if no documents are loaded raise the exception
                
            self.log.info("All documents loaded", total_docs=len(documents), session_id=self.session_id)
            return self._create_retriever(documents)  #create the retriever using the loaded documents
                  
        except Exception as e:
            self.log.error("Failed to ingest files", error=str(e))
            raise DocumentPortalException("Ingestion error in DocumentIngestor", sys)
        

    def _create_retriever(self, documents):
        try:
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=300) #define the text splitter
            chunks = splitter.split_documents(documents)  #split the documents into chunks
            self.log.info("Documents split into chunks", total_chunks=len(chunks), session_id=self.session_id)
            
            embeddings = self.model_loader.load_embeddings()  #initialize the embeddings model
            vectorstore = FAISS.from_documents(documents=chunks, embedding=embeddings) #define the FAISS vectorstore
            
            # Save FAISS index under session folder
            vectorstore.save_local(str(self.session_faiss_dir)) #save the index in the session_faiss_dir
            self.log.info("FAISS index saved to disk", path=str(self.session_faiss_dir), session_id=self.session_id)
            
            retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5}) #use the vectorstore to create the retriever
            
            self.log.info("FAISS retriever created and ready to use", session_id=self.session_id)
            return retriever
            
        except Exception as e:
            self.log.error("Failed to create retriever", error=str(e))
            raise DocumentPortalException("Retrieval error in DocumentIngestor", sys)