from pydantic import BaseModel, Field
from typing import List

class Row(BaseModel):
    Date: str = Field(..., description = 'Date of the row')
    Location: str = Field(..., description = 'Location of the row')
    Breakfast_provided: bool = Field(..., description = 'Whether breakfast was provided or not')
    Lunch_provided: bool = Field(..., description = 'Whether lunch was provided or not')
    Dinner_provided: bool = Field(..., description = 'Whether dinner was provided or not')
    Allowance: float = Field(..., description = 'The allowance for the row')

class Table(BaseModel):
    rows: List[Row] = Field(..., description = 'List of rows in the table')