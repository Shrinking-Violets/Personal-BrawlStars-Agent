from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from services.brawl_client import BrawlStarsClient
from services.vectorstore import PatchVectorStore

app = FastAPI(title = 'BrawlRAG')

brawl_client = BrawlStarsClient()
vector_store = PatchVectorStore()

class QueryRequest(BaseModel):
    player_tag: str
    message: str

@app.post("/query")
async def query(request: QueryRequest):
    try:
        profile = await brawl_client.get_player_profile(request.player_tag)
        top_brawler = max(profile.brawlers, key=lambda b: b.trophies)
        
        search_results = vector_store.search(
            query=request.message, 
            n_results=3,
            brawler_name=top_brawler.name.capitalize()
        )
        retrieved_patches = search_results.get("documents", [[]])[0]

        return {
            "user_status": f"Player {profile.name} found. Top Brawler is {top_brawler.name}.",
            "retrieved_context": retrieved_patches,
            "next_step": "Ready to send to LLM!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def home():
    return {"message": "BrawlRAG API is live! Go to /docs to test endpoints."}