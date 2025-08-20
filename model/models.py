# We have to keep all the pydantic models here
# Pydatic is required for the data validation
# The data must follow the schema defined in this pydatic model

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any