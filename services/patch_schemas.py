from typing import List, Optional, Literal
from pydantic import BaseModel


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