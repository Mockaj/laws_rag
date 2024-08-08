import os
from voyageai import Client
import voyageai.error as error
from typing import List, Optional
from dotenv import load_dotenv


VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
load_dotenv()

def serve_async_client():
    try:
        client = Client(api_key=VOYAGE_API_KEY)
        return client
    except:
        raise error.VoyageError("Error serving Voyage client")
    

async def embed(text: List[str], input_type: str = "query"):
    vo = serve_async_client()
    result = vo.embed(text, model="voyage-multilingual-2", input_type=input_type)
    return result.embeddings[0]

async def rerank(query: str, documents: List[str], model: str, top_k: Optional[int] = None, truncation: bool = True):
    vo = serve_async_client()
    reranking_object =  vo.rerank(
        query=query,
        documents=documents,
        model=model,
        top_k=top_k,
        truncation=truncation
    )
    return reranking_object.results