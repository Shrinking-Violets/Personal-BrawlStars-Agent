import chromadb
import uuid
from typing import List, Optional
from .patch_schemas import BalanceChange

class PatchVectorStore:
    def __init__(self, db_path: str = "./chroma_db"):

        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="brawl_patches")

    def add_changes(self, changes: List[BalanceChange]):
        """Takes a list of BalanceChange objects and inserts them into ChromaDB."""
        ids = []
        documents = []
        metadatas = []

        for change in changes:
            unique_id = str(uuid.uuid4())
            ids.append(unique_id)

            doc_text = (
                f"In Patch {change.patch_version} ({change.release_date}), "
                f"{change.brawler} received a {change.change_type} to their {change.change_target}. "
                f"Details: {change.description}"
            )
            documents.append(doc_text)

            meta = {
                "patch_version": change.patch_version,
                "release_date": change.release_date,
                "brawler": change.brawler,
                "change_type": change.change_type,
                "change_target": change.change_target
            }
            metadatas.append(meta)

        if ids:
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            print(f"Successfully inserted {len(ids)} records into ChromaDB!")

    def search(self, query: str, n_results: int = 3, brawler_name: Optional[str] = None):
        """Perform a semantic search, optionally filtering by a specific brawler."""
        where_clause = {"brawler": brawler_name} if brawler_name else None
        
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_clause
        )
        return results