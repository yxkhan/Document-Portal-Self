
import os
import sys
from utils.model_loader import ModelLoader
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from model.models import *
from langchain_core.output_parsers import JsonOutputParser
from langchain.output_parsers import OutputFixingParser
from prompt.prompt_library import *


class DocumentAnalyzer:
    """
    Analyzes documents using a pre-trained model.
    Automatically logs all actions and supports session-based organization.
    """
    def __init__(self):
        self.log = CustomLogger().get_logger(__name__)
        try:
            self.loader=ModelLoader()    # Load the model as for analysis we will use capabilities of llm   
            self.llm=self.loader.load_llm()
            
            # Prepare parsers
            self.parser = JsonOutputParser(pydantic_object=Metadata)   # Use pydantic model for output validation
            self.fixing_parser = OutputFixingParser.from_llm(parser=self.parser, llm=self.llm)  #Use OutputFixingParser to ensure the output is valid according to the Metadata model
            
            self.prompt = prompt
            
            self.log.info("DocumentAnalyzer initialized successfully")
            
            
        except Exception as e:
            self.log.error(f"Error initializing DocumentAnalyzer: {e}")
            raise DocumentPortalException("Error in DocumentAnalyzer initialization", sys)


    def analyze_document(self):
        """Actual document analysis method"""
        pass