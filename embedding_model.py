from typing import List
from sentence_transformers import SentenceTransformer

# model = SentenceTransformer('intfloat/multilingual-e5-large-instruct')
model = SentenceTransformer("BAAI/bge-m3")


def get_embeddings(texts: List[str]):
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=False, convert_to_numpy=True)