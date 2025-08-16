import os
import fitz  #wrapper on pymupdf
import uuid  #for generating unique IDs
from datetime import datetime
from logger.custom_logger import CustomLogger
from exceptions.custom_exceptions import DocumentPortalException