from services.patch_parser import parse_patch_notes

# Use the file you created in Step 2.2
FILE_PATH = "data/raw_patch_53.txt" 
PATCH_VERSION = "v53.0"
RELEASE_DATE = "2026-08-04" 

def main():
    try:
        changes = parse_patch_notes(FILE_PATH, PATCH_VERSION, RELEASE_DATE)
        
        print(f"✅ Successfully parsed {len(changes)} balance changes!\n")
        
        for idx, change in enumerate(changes):
            print(f"Change #{idx + 1}")
            print(f"  Brawler: {change.brawler}")
            print(f"  Type: {change.change_type}")
            print(f"  Target: {change.change_target}")
            print(f"  Old Value: {change.old_value} | New Value: {change.new_value}")
            print(f"  Description: {change.description}\n")
            
    except Exception as e:
        print(f"❌ Error parsing file: {e}")

if __name__ == "__main__":
    main()