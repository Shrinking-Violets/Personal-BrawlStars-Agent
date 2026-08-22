import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document

def scrape_release_notes(url: str) -> list[Document]:
    """
    Scrapes the release notes from the given URL and returns a list of Document objects.
    Each Document contains the text of a release note and its metadata.
    """
    response = requests.get(url)
    response.raise_for_status()  # Raise an error for bad responses

    soup = BeautifulSoup(response.text, 'html.parser')
    
    release_notes_divs = soup.find_all('div', class_='archived-articles')
    
    documents = []
    
    for div in release_notes_divs:
        title = div.find('h2').get_text(strip=True) if div.find('h2') else "Untitled Release Note"
        content = div.get_text(separator="\n", strip=True)
        
        doc = Document(
            page_content=content,
            metadata={"title": title, "source_url": url}
        )
        documents.append(doc)
    
    return documents