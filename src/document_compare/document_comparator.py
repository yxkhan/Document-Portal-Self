import sys
from dotenv import load_dotenv
import pandas as pd
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from model.models import *
from prompt.prompt_library import PROMPT_REGISTRY
from utils.model_loader import ModelLoader
from langchain_core.output_parsers import JsonOutputParser
from langchain.output_parsers import OutputFixingParser


class DocumentComparatorLLM:
    def __init__(self):    
        load_dotenv()  # Load environment variables (like API keys)
        self.log = CustomLogger().get_logger(__name__)  # Setup logger
        self.loader = ModelLoader()  # Initialize model loader utility
        self.llm = self.loader.load_llm()  # Load the actual LLM for comparison
        
        self.parser = JsonOutputParser(pydantic_object=SummaryResponse)  # Parse output into SummaryResponse format
        self.fixing_parser = OutputFixingParser.from_llm(parser=self.parser, llm=self.llm)  # Fix invalid JSON if needed
        
        self.prompt = PROMPT_REGISTRY["document_comparison"]  # Get the comparison prompt
        self.chain = self.prompt | self.llm | self.parser  # Create pipeline: prompt → LLM → JSON parser
        
        self.log.info("DocumentComparatorLLM initialized with model and parser.")  # Log init success

    def compare_documents(self, combined_docs: str) -> pd.DataFrame:
        """Compares two documents and returns a structured comparison."""
        try:
            inputs = {
                "combined_docs": combined_docs,  # Combined text of PDFs
                "format_instruction": self.parser.get_format_instructions()  # Expected JSON schema
            }
            self.log.info("Starting document comparison", inputs=inputs)  # Log start
            
            response = self.chain.invoke(inputs)  # Run chain and get structured response
            self.log.info("Document comparison completed", response=response)  # Log completion
            
            return self._format_response(response)  # Convert response to DataFrame

        except Exception as e:
            self.log.error(f"Error in compare_documents: {e}")  # Log error
            raise DocumentPortalException("An error occurred while comparing documents.", sys)  # Raise custom error

    def _format_response(self, response_parsed: list[dict]) -> pd.DataFrame:
        """Formats the response from the LLM into a structured format."""
        try:
            df = pd.DataFrame(response_parsed)  # Convert parsed JSON into DataFrame
            self.log.info("Response formatted into DataFrame", dataframe=df)  # Log success
            return df  # Return DataFrame

        except Exception as e:
            self.log.error("Error formatting response into DataFrame", error=str(e))  # Log error
            raise DocumentPortalException("Error formatting response", sys)  # Raise custom error
