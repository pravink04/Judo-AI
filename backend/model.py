from pydantic import BaseModel
from typing import TypedDict

class TicketRequest(BaseModel):
    message: str

class TicketResponse(BaseModel):
    response: str

# Updated State with 'context'
class TicketState(TypedDict):
    message: str
    category: str
    context: str  
    response: str