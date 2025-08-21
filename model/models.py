# We have to keep all the pydantic models here
# Pydatic is required for the data validation
# The data must follow the schema defined in this pydatic model

from pydantic import BaseModel, Field, RootModel
from typing import Optional, List, Dict, Any
from typing import Optional, List, Dict, Any, Union

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
