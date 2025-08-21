import sys
from pathlib import Path
import fitz
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException

class DocumentIngestion:
    def __init__(self,base_dir:str="data\\document_compare"):
        self.log = CustomLogger().get_logger(__name__)
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
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
            pass
            self.delete_existing_files()     #Deleting the existing files if any
            self.log.info("Existing files deleted successfully.")
            
            ref_path = self.base_dir/ reference_file.name    #reference_file is the file uploaded by the user (v1)
            act_path = self.base_dir / actual_file.name     #actual_file is the file uploaded by the user (v2)
            
            if not reference_file.name.endswith(".pdf") or not actual_file.name.endswith(".pdf"):  #if these files are not pdf then raise value error
                raise ValueError("Only PDF files are allowed.")
            
            with open(ref_path, "wb") as f:     #opens the file
                f.write(reference_file.getbuffer())

            with open(act_path, "wb") as f:      #opens the file
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