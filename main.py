import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from services.agent import BrawlAgent

load_dotenv()

app = FastAPI(title="BrawlRAG Agentic Copilot API")
agent = BrawlAgent()

class ChatRequest(BaseModel):
    player_tag: str
    message: str

@app.get("/")
def health_check():
    return {"status": "ok", "message": "BrawlRAG Agent API is live."}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        reply = await agent.run(
            player_tag=request.player_tag,
            user_message=request.message
        )
        return {
            "player_tag": request.player_tag,
            "response": reply
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))