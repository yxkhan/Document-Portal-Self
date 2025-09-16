from __future__ import annotations
from pathlib import Path
from typing import Iterable, List
from fastapi import UploadFile
from langchain.schema import Document
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
log = CustomLogger().get_logger(__name__)
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def load_documents(paths: Iterable[Path]) -> List[Document]:
    """
    Load documents from local file paths into LangChain Document objects.
    - Uses different loaders depending on file extension.
    - Supported: PDF, DOCX, TXT.
    - Returns a flat list of Document objects with content + metadata.
    """
    docs: List[Document] = []
    try:
        for p in paths:
            ext = p.suffix.lower()

            # Choose loader based on extension
            if ext == ".pdf":
                loader = PyPDFLoader(str(p))       # LangChain loader for PDFs
            elif ext == ".docx":
                loader = Docx2txtLoader(str(p))    # Loader for Word documents
            elif ext == ".txt":
                loader = TextLoader(str(p), encoding="utf-8")  # Simple text loader
            else:
                # Skip if not supported
                log.warning("Unsupported extension skipped", path=str(p))
                continue

            # Load documents from file → returns list[Document]
            docs.extend(loader.load())

        # Log how many docs were ingested
        log.info("Documents loaded", count=len(docs))
        return docs

    except Exception as e:
        # If anything goes wrong, wrap in custom exception
        log.error("Failed loading documents", error=str(e))
        raise DocumentPortalException("Error loading documents", e) from e


def concat_for_analysis(docs: List[Document]) -> str:
    """
    Combine multiple Document objects into a single text blob.
    Adds the source file info for traceability.
    
    Example Output:
    --- SOURCE: report.pdf ---
    <page_content>
    """
    parts = []
    for d in docs:
        # Try to fetch metadata for source name
        src = d.metadata.get("source") or d.metadata.get("file_path") or "unknown"
        parts.append(f"\n--- SOURCE: {src} ---\n{d.page_content}")

    # Join all docs together into one string
    return "\n".join(parts)


def concat_for_comparison(ref_docs: List[Document], act_docs: List[Document]) -> str:
    """
    Create a structured string for comparison.
    Splits documents into <<REFERENCE>> and <<ACTUAL>> sections.

    Example Output:
    <<REFERENCE_DOCUMENTS>>
    --- SOURCE: ref.pdf ---
    <ref_content>

    <<ACTUAL_DOCUMENTS>>
    --- SOURCE: act.pdf ---
    <act_content>
    """
    left = concat_for_analysis(ref_docs)   # Prepare reference docs text
    right = concat_for_analysis(act_docs)  # Prepare actual docs text
    return f"<<REFERENCE_DOCUMENTS>>\n{left}\n\n<<ACTUAL_DOCUMENTS>>\n{right}"


# ---------- Helpers ----------
class FastAPIFileAdapter:
    # This class adapts FastAPI's UploadFile object
    # to look like a regular file object with `.name` and `.getbuffer()` methods,
    # which some libraries expect (adapter pattern).

    def __init__(self, uf: UploadFile):
        # Constructor receives an UploadFile object (from FastAPI)
        self._uf = uf                # store the original UploadFile object internally
        self.name = uf.filename      # expose the file's name as an attribute (e.g., "report.pdf")

    def getbuffer(self) -> bytes:
        # Return the raw bytes of the uploaded file, this is called as fallback refer to read_pdf method
        self._uf.file.seek(0)        # reset the file pointer to the beginning
        return self._uf.file.read()  # read the entire file content into memory as bytes


def read_pdf_via_handler(handler, path: str) -> str:
    """Use to read pdf via handler and return its text content"""
    
    # Check if the handler has a method named 'read_pdf'
    if hasattr(handler, "read_pdf"):
        # If it exists, call it with the file path and return the extracted text
        return handler.read_pdf(path)  # type: ignore

    # Check if the handler has a method named 'read_'
    if hasattr(handler, "read_"):
        # If it exists, call it with the file path and return the extracted text
        return handler.read_(path)  # type: ignore

    # If the handler has neither 'read_pdf' nor 'read_' method, raise an error
    # This ensures we do not silently fail
    raise RuntimeError("DocHandler has neither read_pdf nor read_ method.")

# Abstraction
# Your main code doesn’t need to know exactly which method the handler uses.
# The function takes care of checking .read_pdf or .read_ and calling the correct one.
# Backward compatibility / flexibility
# Supports multiple handler implementations.
# If tomorrow you swap DocHandler with SomeOtherHandler that only has .read_(), your main code doesn’t break.
# Error safety
# If the handler has neither method, it raises a clear RuntimeError.
# If you called dh.read_pdf(saved_path) blindly and the method didn’t exist, Python would raise AttributeError, which is less informative.
# Cleaner main code
# Main logic stays simple: just text = read_pdf_via_handler(dh, saved_path)
# The details of which method to call are hidden inside the helper.
