
import os
import json
import logging
from typing import List, Dict, Any
from pydantic import BaseModel
from langchain.text_splitter import RecursiveCharacterTextSplitter
# from embeddings_openai import embed_large as get_embedding
# from embeddings_openai import embed_small as get_embedding
from voyage import embed as get_embedding
from voyage import count_tokens
from voyage import tokenize
# from modules.embedding_model import get_embeddings as get_embedding

import os
os.environ['HF_TOKEN'] = 'your_hugging_face_token'

# Configure logging
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'logs.log')

logging.basicConfig(
    filename=log_file, 
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# Utility functions
def load_from_json(filename: str) -> Any:
    logging.debug(f"Loading data from {filename}")
    with open(filename, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    logging.debug(f"Data loaded successfully from {filename}")
    return data['data']

def save_to_json(data: Any, filename: str) -> None:
    logging.debug(f"Saving data to {filename}")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logging.debug(f"Data saved successfully to {filename}")

# Pydantic models for data validation and structure
class ChunkedData(BaseModel):
    text: str
    embedding: List[float]

class ProcessedEntry(BaseModel):
    name: ChunkedData
    introduction: ChunkedData
    chunks: Dict[str, ChunkedData]

# Function to process and chunk data
def process_data(entry: Dict[str, Any], chunk_size: int, chunk_overlap: int) -> ProcessedEntry:
    logging.debug(f"Processing entry")
    name = entry['name']
    introduction = entry['detail']['introduction']
    description = entry['detail']['description']
    
    logging.debug(f"Name: {name}")
    intro_snippet = introduction[:50].replace('\n', '')
    logging.debug(f"Introduction: {intro_snippet}...")
    logging.debug(f"Description length: {len(description)}")
    
    # Initialize the text splitter
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    # Split the description into chunks
    chunks = text_splitter.split_text(description)
    logging.debug(f"Description split into {len(chunks)} chunks")
    
    # Generate embeddings
    name_embedding = get_embedding(name)
    intro_embedding = get_embedding(introduction)
    
    chunked_data = {}
    for i, chunk in enumerate(chunks):
        chunk_key = f'chunk_{i:04d}'
        chunk_embedding = get_embedding([chunk])
        chunked_data[chunk_key] = ChunkedData(text=chunk, embedding=list(chunk_embedding))
        
        # Print progress of chunking and embedding
        percent_complete = (i + 1) / len(chunks) * 100
        print(f"Processing {name}: {percent_complete:.2f}% complete")

    logging.debug("Entry processed successfully")
    return ProcessedEntry(
        name=ChunkedData(text=name, embedding=name_embedding),
        introduction=ChunkedData(text=introduction, embedding=intro_embedding),
        chunks=chunked_data
    )

# Main function to process all files in the data directory
def process_all_files(data_dir: str, db_dir: str, chunk_size: int, chunk_overlap: int) -> None:
    logging.debug(f"Processing all files in directory: {data_dir}")
    
    filenames = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    num_files = len(filenames)
    
    for idx, filename in enumerate(filenames, start=1):
        # print(f"Processing file {idx}/{num_files}: {filename}", end='\r')
        logging.debug(f"Processing file: {filename}")
        
        if not os.path.exists(db_dir):
            logging.debug(f"Database directory {db_dir} does not exist. Creating it.")
            os.makedirs(db_dir)
        
        # Load data
        file_path = os.path.join(data_dir, filename)
        data = load_from_json(file_path)
        
        # Process data
        processed_entries = [
            process_data(entry, chunk_size, chunk_overlap)
            for entry in data
        ]
        
        # Save processed data
        output_filename = f"{os.path.splitext(filename)[0]}_chunked.json"
        output_path = os.path.join(db_dir, output_filename)
        save_to_json([entry.dict() for entry in processed_entries], output_path)
        
        logging.debug(f"File processed and saved: {output_filename}")

# Example usage
if __name__ == "__main__":
    chunk_size = 20000  # Set your desired chunk size
    chunk_overlap = 2000  # Set your desired chunk overlap
    data_dir = 'data'
    db_dir = f'db/db_VOYAGE_MULTILINGUAL_embed_{chunk_size}_{chunk_overlap}'
    
    process_all_files(data_dir, db_dir, chunk_size, chunk_overlap)

