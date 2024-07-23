import voyageai
import logging
from typing import List
from pymongo import MongoClient
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct
from pydantic import BaseModel
from qdrant_client.models import VectorParams, Distance

DIMENSION = 1024
vo = voyageai.Client()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("process.log"),
    logging.StreamHandler()
])

# Define your data model
class Paragraf(BaseModel):
    cislo: str
    zneni: str
    law_name: str
    year: str

def embed(text, input_type="document"):
    try:
        result = vo.embed(text, model="voyage-multilingual-2", input_type=input_type)
        return result.embeddings[0]
    except Exception as e:
        logging.error(f"Error embedding text: {text[:30]}... - {e}")
        raise

# Function to load data from MongoDB
def load_paragraphs_from_mongodb(db_name: str) -> List[Paragraf]:
    try:
        client = MongoClient("mongodb://localhost:27017/")
        db = client[db_name]
        collection_names = db.list_collection_names()
        
        paragraphs = []
        for collection_name in collection_names:
            collection = db[collection_name]
            for doc in collection.find():
                paragraph = Paragraf(
                    cislo=doc['cislo'],
                    zneni=doc['zneni'],
                    law_name=doc['law_name'],
                    year=doc['year']
                )
                paragraphs.append(paragraph)
        return paragraphs
    except Exception as e:
        logging.error(f"Error loading data from MongoDB: {e}")
        raise

# Function to process and embed paragraphs, then save to Qdrant
def process_and_save_to_qdrant(paragraphs: List[Paragraf], collection_name: str, qdrant_host: str = "localhost", qdrant_port: int = 6333):
    try:
        client = QdrantClient(host=qdrant_host, port=qdrant_port)
        vectors_config = VectorParams(
            size=DIMENSION,
            distance=Distance.COSINE,
        )
        # Ensure the collection exists
        if not client.get_collection(collection_name):
            client.create_collection(collection_name, vectors_config=vectors_config)
        else:
            client.delete_collection(collection_name)
            client.create_collection(collection_name, vectors_config=vectors_config)

        total_paragraphs = len(paragraphs)
        processed_paragraphs = 0

        for i, paragraph in enumerate(paragraphs):
            if paragraph.zneni is None or paragraph.zneni == "":
                logging.warning(f"Skipping empty paragraph: {paragraph}")
                continue
            try:
                embedding = embed(paragraph.zneni)
                point = PointStruct(
                    id=i+1,
                    vector=embedding,
                    payload={
                        "cislo": paragraph.cislo,
                        "zneni": paragraph.zneni,
                        "law_name": paragraph.law_name,
                        "year": paragraph.year
                    }
                )
                client.upsert(collection_name=collection_name, points=[point])
                processed_paragraphs += 1
                logging.info(f"Processed {processed_paragraphs}/{total_paragraphs} paragraphs")
            except Exception as e:
                logging.error(f"Error processing paragraph {i+1}: {e}")
        
        logging.info(f"Finished inserting {processed_paragraphs} paragraphs into collection '{collection_name}'.")

    except Exception as e:
        logging.error(f"Error setting up Qdrant collection: {e}")
        raise

if __name__ == '__main__':
    mongo_db_name = "law_database"  # Specify your MongoDB database name here
    qdrant_collection_name = "legal_paragraphs"  # Specify your Qdrant collection name here

    try:
        # Load data from MongoDB
        paragraphs = load_paragraphs_from_mongodb(mongo_db_name)
        
        # Process and save to Qdrant
        process_and_save_to_qdrant(paragraphs, qdrant_collection_name)
    except Exception as e:
        logging.error(f"Error in main execution: {e}")
