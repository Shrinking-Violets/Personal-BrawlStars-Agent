from services.patch_parser import parse_patch_notes
from services.vectorstore import PatchVectorStore

# Your existing file paths
FILE_PATH = "data/raw_patch_53.txt" 
PATCH_VERSION = "v53.0"
RELEASE_DATE = "2026-08-04"

def main():
    print("1. Parsing raw text...")
    changes = parse_patch_notes(FILE_PATH, PATCH_VERSION, RELEASE_DATE)
    
    print("2. Initializing Vector Database...")
    db = PatchVectorStore()
    
    print("3. Indexing data...")
    db.add_changes(changes)
    
    print("\n4. 🔍 Testing Semantic Search:")
    query = "What happened to Damian's fire punch?"
    print(f"Query: '{query}'")
    
    
    search_results = db.search(query=query, n_results=2, brawler_name="Damian")
    
    
    docs = search_results.get("documents", [[]])[0]
    
    for i, doc in enumerate(docs):
        print(f"\nResult {i+1}:")
        print(f" - {doc}")

if __name__ == "__main__":
    main()