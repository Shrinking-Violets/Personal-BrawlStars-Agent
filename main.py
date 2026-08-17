import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel
from services.brawl_client import BrawlStarsClient
from services.vectorstore import PatchVectorStore

# Load environment variables (.env)
load_dotenv()


app = FastAPI(title="BrawlRAG Copilot API")

brawl_client = BrawlStarsClient()
vector_store = PatchVectorStore()
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class ChatRequest(BaseModel):
    player_tag: str
    message: str


@app.get("/")
def health_check():
    return {"status": "ok", "message": "BrawlRAG API is live. Visit /docs to test endpoints."}


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        profile = await brawl_client.get_player_profile(request.player_tag)
        top_brawler = max(profile.brawlers, key=lambda b: b.trophies)

        search_results = vector_store.search(
            query=request.message,
            n_results=3,
            brawler_name=top_brawler.name.capitalize()
        )

        docs = search_results.get("documents", [[]])[0]
        context_string = "\n".join(docs) if docs else "No specific patch notes found for this brawler."

        system_prompt = f"""
You are an expert Brawl Stars balance and coaching assistant.
Answer the user's query accurately using ONLY the provided player context and patch history.

--- LIVE PLAYER PROFILE ---
- Player: {profile.name}
- Total Trophies: {profile.trophies}
- Top Brawler: {top_brawler.name} (Trophies: {top_brawler.trophies}, Power: {top_brawler.power})

--- RETRIEVED PATCH NOTES ---
{context_string}

--- GUIDELINES ---
- Base your advice directly on the patch numbers and player stats above.
- If specific numbers are requested, state them explicitly as listed in the patch notes.
- Keep recommendations concise and actionable.
"""

        completion = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": request.message}
            ],
            temperature=0.2
        )

        llm_reply = completion.choices[0].message.content

        return {
            "player": profile.name,
            "top_brawler": top_brawler.name,
            "response": llm_reply
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))