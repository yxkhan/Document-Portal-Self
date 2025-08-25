# We have to keep all the pydantic models here
# Pydatic is required for the data validation
# The data must follow the schema defined in this pydatic model

from pydantic import BaseModel, Field, RootModel
from typing import Optional, List, Dict, Any, Union
from enum import Enum

#This is for Document Analysis pydantic model
class Metadata(BaseModel):
    """This defines what all thing we need while analysing the document"""
    Summary: List[str] = Field(default_factory=list, description="Summary of the document")
    Title: str
    Author: str
    DateCreated: str   
    LastModifiedDate: str
    Publisher: str
    Language: str
    PageCount: Union[int, str]  # Can be "Not Available"
    SentimentTone: str

#This class for Document comparison pydantic model
class ChangeFormat(BaseModel):
    Page: str
    changes: str

class SummaryResponse(RootModel[list[ChangeFormat]]):
    pass

# This is for Contextual Question Answering pydantic model
# Its important in the industry level project
# We are using Enum class to define the prompt type
#Sunny will explain you about Enum in the next class
class PromptType(str, Enum):
    DOCUMENT_ANALYSIS = "document_analysis"
    DOCUMENT_COMPARISON = "document_comparison"
    CONTEXTUALIZE_QUESTION = "contextualize_question"
    CONTEXT_QA = "context_qa"