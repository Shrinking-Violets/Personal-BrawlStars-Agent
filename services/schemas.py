from typing import List
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