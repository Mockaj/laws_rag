import os
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_HOST = os.getenv("QDRANT_HOST")

collection_name = "legal_paragraphs_updated"
cloud_client = QdrantClient(
    url=QDRANT_HOST, 
    api_key=QDRANT_API_KEY,
)

local_client = QdrantClient("localhost",port=6333)
local_client.migrate(cloud_client,[collection_name],batch_size = 100, recreate_on_collision=True)