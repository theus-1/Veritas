from app.clients.gnews_client import GNewsClient
from app.core.config import Config


class SearchService:

    def __init__(self):
        self.config = Config()
        self.client = GNewsClient(self.config)

    def search(self, query: str):
        return self.client.search(query)
