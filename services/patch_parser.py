import re
from typing import List
from services.patch_schemas import BalanceChange

def parse_patch_notes(filepath: str, patch_version: str, release_date: str) -> List[BalanceChange]:
    """
    Parses a simplified raw text file of patch notes and returns a list of BalanceChange objects.
    """
    changes: List[BalanceChange] = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_brawler = None
    current_type = None  # "Buff" or "Nerf"

    for line in lines:
        line = line.strip()
        
        if not line:
            continue
    
        if "BUFFS" in line.upper():
            current_type = "Buff"
            current_brawler = None # Reset brawler under new category
            continue
        elif "NERFS" in line.upper():
            current_type = "Nerf"
            current_brawler = None
            continue

        # Logic to identify a Brawler name (usually just a single capitalized word on its own line)
        
        if line.isalpha() and line.istitle():
             current_brawler = line
             continue
        
       
        if current_brawler and current_type and len(line) > 5:
            
            target = "Base Stats"
            if "Gadget" in line: target = "Gadget"
            elif "Star Power" in line: target = "Star Power"
            elif "NanoPower" in line: target = "NanoPower"

            # Attempt to extract old/new values if the line uses ">" or "->" or "to"
            old_val = None
            new_val = None
            
            match = re.search(r'from\s+([0-9%]+)\s*(?:>|->|to|➡️)\s*([0-9%]+)', line, re.IGNORECASE)
            if match:
                old_val = match.group(1)
                new_val = match.group(2)

            change = BalanceChange(
                patch_version=patch_version,
                release_date=release_date,
                brawler=current_brawler,
                change_target=target,
                change_type=current_type,
                description=line,
                old_value=old_val,
                new_value=new_val
            )
            changes.append(change)

    return changes