import logging
import tiktoken
from pymongo import MongoClient
from typing import List, Dict
from pydantic import BaseModel



# Define your data model
class Paragraf(BaseModel):
    cislo: str
    zneni: str
    law_name: str
    year: str
    isValid: bool
    staleURL: str

def extract_year_from_staleURL(staleURL: str) -> str:
    try:
        parts = staleURL.split('/')
        if len(parts) > 2:
            return parts[2]
        return "Unknown"
    except Exception as e:
        logging.error(f"Error extracting year from staleURL {staleURL}: {e}")
        return "Unknown"

# Function to load data from MongoDB
def load_paragraphs_from_mongodb(db_name: str) -> Dict[str, Paragraf]:
    try:
        client = MongoClient("mongodb://localhost:27017/")
        db = client[db_name]
        collection_names = db.list_collection_names()

        paragraphs = {}
        for collection_name in collection_names:
            collection = db[collection_name]
            for doc in collection.find():
                year = extract_year_from_staleURL(doc['staleURL'])
                paragraph = Paragraf(
                    cislo=doc['cislo'],
                    zneni=doc['zneni'],
                    law_name=doc['law_name'],
                    year=year,
                    isValid=doc.get('isValid', None),
                    staleURL=doc.get('staleURL', None)
                )
                key = f"{paragraph.cislo}|{paragraph.law_name}|{paragraph.year}"
                paragraphs[key] = paragraph
        return paragraphs
    except Exception as e:
        logging.error(f"Error loading data from MongoDB: {e}")
        raise
    
def count_total_tokens(paragraphs: Dict[str, Paragraf]) -> int:
    # Initialize tokenizer
    encoding = tiktoken.get_encoding("cl100k_base")  # Use appropriate model encoding here

    total_tokens = 0
    for key, paragraph in paragraphs.items():
        # Encode text to tokens
        tokens = encoding.encode(paragraph.zneni)
        # Count the number of tokens
        total_tokens += len(tokens)
    
    return total_tokens

# Example usage
if __name__ == "__main__":
    db_name = "law_database"
    paragraphs = load_paragraphs_from_mongodb(db_name)
    total_tokens = count_total_tokens(paragraphs)
    print(f"Total number of tokens: {total_tokens}")