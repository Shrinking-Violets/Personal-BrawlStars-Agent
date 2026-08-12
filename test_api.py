import os
import asyncio
import httpx
from dotenv import load_dotenv


load_dotenv()
SUPERCELL_TOKEN = os.getenv("SUPERCELL_API_KEY")

PLAYER_TAG = "#9CRYGLC"
async def test_brawl_stars_api():
    if not SUPERCELL_TOKEN:
        print("❌ Error: API Token not found. Check your .env file.")
        return
    formatted_tag = PLAYER_TAG.replace("#", "%23")    
    profile_url = f"https://api.brawlstars.com/v1/players/{formatted_tag}"
    headers = {"Authorization": f"Bearer {SUPERCELL_TOKEN}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(profile_url, headers=headers)
        
        if response.status_code == 403:
            print("❌ 403 Forbidden: The IP address you whitelisted on the Developer Portal doesn't match your current network IP.")
            return
        elif response.status_code != 200:
            print(f"❌ Error {response.status_code}: {response.text}")
            return
            
        data = response.json()
        
       
        print(f"Player Name: {data.get('name')}")
        print(f"Total Trophies: {data.get('trophies')}")
        
        print("\n🏆 Top 3 Brawlers:")
        brawlers = sorted(data.get('brawlers', []), key=lambda x: x.get('trophies', 0), reverse=True)
        
        for b in brawlers[:3]:
            print(f" - {b['name']}: {b['trophies']} Trophies (Power {b['power']})")

if __name__ == "__main__":
    asyncio.run(test_brawl_stars_api())