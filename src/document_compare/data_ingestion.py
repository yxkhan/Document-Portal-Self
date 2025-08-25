import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
import fitz
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException

class DocumentIngestion:
    def __init__(self,base_dir:str="data\\document_compare", session_id=None):
        self.log = CustomLogger().get_logger(__name__)
        self.base_dir = Path(base_dir)  #Base directory where the data would be available
        #self.base_dir.mkdir(parents=True, exist_ok=True)

        # Generate a unique session ID based on the current time and a random UUID for data versioning
        self.session_id = session_id or f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        self.session_path = self.base_dir / self.session_id
        self.session_path.mkdir(parents=True, exist_ok=True)

        self.log.info("DocumentComparator initialized", session_path=str(self.session_path))
    
    def delete_existing_files(self):
        """
        Deletes existing files at the specified paths.
        """
        try:
            if self.base_dir.exists() and self.base_dir.is_dir():
                for file in self.base_dir.iterdir():
                    if file.is_file():
                        file.unlink()      #unlink means delete it
                        self.log.info("File deleted", path=str(file))
                self.log.info("Directory cleaned", directory=str(self.base_dir))
        except Exception as e:
            self.log.error(f"Error deleting existing files: {e}")
            raise DocumentPortalException("An error occurred while deleting existing files.", sys)
     
    def save_uploaded_files(self,reference_file,actual_file):
        """
        Saves uploaded files to a specific directory.
        """
        try:
            # self.delete_existing_files()     #Deleting the existing files if any
            # self.log.info("Existing files deleted successfully.")
            
            ref_path = self.session_path/ reference_file.name    #reference_file is the file uploaded by the user (v1)
            act_path = self.session_path / actual_file.name     #actual_file is the file uploaded by the user (v2)
            
            if not reference_file.name.endswith(".pdf") or not actual_file.name.endswith(".pdf"):  #if these files are not pdf then raise value error
                raise ValueError("Only PDF files are allowed.")
            
            with open(ref_path, "wb") as f:     #opens the file buffer
                f.write(reference_file.getbuffer())

            with open(act_path, "wb") as f:      #opens the file in buffer
                f.write(actual_file.getbuffer())

            self.log.info("Files saved", reference=str(ref_path), actual=str(act_path))
            return ref_path, act_path   
        except Exception as e:
            self.log.error(f"Error saving uploaded files: {e}")
            raise DocumentPortalException("An error occurred while saving uploaded files.", sys)

    
    def read_pdf(self,pdf_path: Path)-> str:
        """
        Reads a PDF file and extracts text from each page.
        """
        try:
             with fitz.open(pdf_path) as doc:
                if doc.is_encrypted:        #just checking if the pdf_doc is encrypted, if so raise value error
                    raise ValueError(f"PDF is encrypted: {pdf_path.name}")
                all_text = []
                for page_num in range(doc.page_count):    #reading each page of the pdf_doc
                    page=doc.load_page(page_num)
                    text = page.get_text()                # extracting text from the page
                    if text.strip():
                        all_text.append(f"\n --- Page {page_num + 1} --- \n{text}")   # appending the text to all_text list 
                self.log.info("PDF read successfully", file=str(pdf_path), pages=len(all_text))
                return "\n".join(all_text)          #Join all the lines
        except Exception as e:
            self.log.error(f"Error reading PDF: {e}")
            raise DocumentPortalException("An error occurred while reading the PDF.", sys)


    def combine_documents(self)->str:
        try:
            content_dict = {}
            doc_parts = []

            for filename in sorted(self.base_dir.iterdir()):
                if filename.is_file() and filename.suffix == ".pdf":
                    content_dict[filename.name] = self.read_pdf(filename)

            for filename, content in content_dict.items():
                doc_parts.append(f"Document: {filename}\n{content}")

            combined_text = "\n\n".join(doc_parts)
            self.log.info("Documents combined", count=len(doc_parts))
            return combined_text

        except Exception as e:
            self.log.error(f"Error combining documents: {e}")
            raise DocumentPortalException("An error occurred while combining documents.", sys)
        
    def clean_old_sessions(self, keep_latest:int = 3):
        """
        Optional method to delete older session folders of data versioning, keeping only the latest N.
        """
        try:
            session_folders = sorted(
                [f for f in self.base_dir.iterdir() if f.is_dir()],
                reverse=True
            )
            for folder in session_folders[keep_latest:]:   #you can mention how many folders you want to keep
                for file in folder.iterdir():
                    file.unlink()
                folder.rmdir()
                self.log.info("Old session folder deleted", path=str(folder))

        except Exception as e:
            self.log.error("Error cleaning old sessions", error=str(e))
            raise DocumentPortalException("Error cleaning old sessions", sys)