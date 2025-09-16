#This is required for file operations such as input/output, reading/writing files, creating directories, etc.
#This is only used in ChatIngestor class

from __future__ import annotations
import os
import sys
import json
import uuid
import hashlib
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Iterable, List, Optional, Dict, Any
from utils.model_loader import ModelLoader
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException

# Setup logger for this module
log = CustomLogger().get_logger(__name__)


# ----------------------------- #
# Helpers (file I/O + loading)  #
# ----------------------------- #

def _session_id(prefix: str = "session") -> str:
    """
    Generate a unique session ID string.
    Format → session_YYYYMMDD_HHMMSS_<random-uuid>
    Example → session_20250916_154533_a1b2c3d4
    Used for grouping files into a session.
    """
    return f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


# Allowed file types for ingestion
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}

def save_uploaded_files(uploaded_files: Iterable, target_dir: Path) -> List[Path]:
    """
    Save uploaded files into a target directory and return their local paths.
    
    - Creates the target directory if it doesn’t exist.
    - Supports only certain file types (pdf, docx, txt).
    - Each file is renamed using a random UUID to avoid collisions.
    - Logs every saved file.
    
    Args:
        uploaded_files: Iterable of uploaded files (from FastAPI, Streamlit, etc.)
        target_dir: Directory where files will be stored.
    
    Returns:
        List of Paths → the local saved file paths.
    """
    try:
        # Make sure the directory exists
        target_dir.mkdir(parents=True, exist_ok=True)
        saved: List[Path] = []

        for uf in uploaded_files:
            # Extract filename & extension
            name = getattr(uf, "name", "file")  # fallback name if no name found
            ext = Path(name).suffix.lower()

            # Skip unsupported formats
            if ext not in SUPPORTED_EXTENSIONS:
                log.warning("Unsupported file skipped", filename=name)
                continue

            # Generate unique filename (avoid clashes between uploads)
            fname = f"{uuid.uuid4().hex[:8]}{ext}" # created a file with unique short uuid + original extension
            out = target_dir / fname

            # Save file content to disk
            with open(out, "wb") as f:
                if hasattr(uf, "read"):          # If file-like object supports .read()
                    f.write(uf.read())
                else:                            # If it’s a memory buffer (e.g. FastAPI UploadFile)
                    f.write(uf.getbuffer())      # fallback method

            # Keep track of saved path
            saved.append(out)

            # Log the action
            log.info("File saved for ingestion", uploaded=name, saved_as=str(out))

        return saved

    except Exception as e:
        # Log + raise custom exception if saving fails
        log.error("Failed to save uploaded files", error=str(e), dir=str(target_dir))
        raise DocumentPortalException("Failed to save uploaded files", e) from e
