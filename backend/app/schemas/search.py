from pydantic import BaseModel

class SearchResult(BaseModel):
    title: str
    url: str
    source_name: str
    snippet: str
