import os
import httpx
from typing import Optional
from .schemas import PlayerProfile

class BrawlStarsClient:
    """Asynchronous client for interacting with the official Supercell Brawl Stars API."""

    BASE_URL = "https://api.brawlstars.com/v1"

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.getenv("SUPERCELL_API_KEY")
        if not self.api_token:
            raise ValueError("❌ SUPERCELL_API_KEY is missing. Please check your .env file.")

        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json"
        }

    async def get_player_profile(self, player_tag: str) -> PlayerProfile:
        """Fetch a player's profile and parse it into a typed PlayerProfile Pydantic schema."""
        # URL encode the tag ('#' becomes '%23')
        formatted_tag = player_tag.replace("#", "%23")
        url = f"{self.BASE_URL}/players/{formatted_tag}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, timeout=10.0)
            response.raise_for_status()
            
            # Pydantic automatically parses and validates the JSON body
            return PlayerProfile.model_validate(response.json())