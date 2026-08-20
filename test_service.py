import asyncio
from services.brawl_client import BrawlStarsClient

async def main():
    client = BrawlStarsClient()
    player_tag = "#9CRYGLC" 
    battle_log = await client.get_battle_log(player_tag)
    print(f"✅ Battle Log Loaded: {len(battle_log.items)} recent battles found.")

    if battle_log.items:
        latest = battle_log.items[0]
        print(f"\n🎮 Latest Match:")
        print(f" - Mode: {latest.event.mode}")
        print(f" - Map: {latest.event.map}")
        print(f" - Result: {latest.battle.result}")
        print(f" - Trophy Change: {latest.battle.trophy_change}")

if __name__ == "__main__":
    asyncio.run(main())