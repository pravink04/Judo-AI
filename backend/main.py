from fastapi import FastAPI, HTTPException
from backend.model import TicketRequest, TicketResponse


from backend.graph import process_ticket 

app = FastAPI(title="AI Ticketing Resolver API")

@app.post("/submit-ticket", response_model=TicketResponse)
async def submit_ticket(request: TicketRequest):
    try:
        # Send ticket to graph.py and get the answer
        ai_response = process_ticket(request.message)
        return TicketResponse(response=ai_response)
    except Exception as e:
        # Catch any unexpected errors cleanly
        raise HTTPException(status_code=500, detail=str(e))