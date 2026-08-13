from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class Brawler(BaseModel):
    name: str
    power: int
    trophies: int
    # Maps the incoming JSON 'highestTrophies' to our Python variable
    highest_trophies: int = Field(alias="highestTrophies")

class PlayerProfile(BaseModel):
    tag: str
    name: str
    trophies: int
    brawlers: List[Brawler]

class Event(BaseModel):
    id: Optional[int] = None
    mode: Optional[str] = None
    map: Optional[str] = None

class Battle(BaseModel):
    result: Optional[str] = None       # e.g. "victory", "defeat", "draw"
    duration: Optional[int] = None
    trophy_change: Optional[int] = Field(default=None, alias="trophyChange")

class BattleLogItem(BaseModel):
    battle_time: Optional[str] = Field(default=None, alias="battleTime")
    event: Event
    battle: Battle

class BattleLog(BaseModel):
    items: List[BattleLogItem]

class BalanceChange(BaseModel):
    # Temporal Data (Crucial for filtering old vs new meta)
    patch_version: str           
    release_date: str             
    
    # Entity Data
    brawler: str                  
    change_target: str            
    
    # Categorization
    change_type: Literal["Buff", "Nerf", "Rework", "Bugfix"]
    attribute: Optional[str] = None  
    
    # The actual raw text from the patch notes
    description: str              
    
    # Optional numeric extraction for advanced agent math
    old_value: Optional[str] = None
    new_value: Optional[str] = None