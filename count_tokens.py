from itertools import count
import os
import json
import tiktoken
from typing import List, Dict, Any
from tqdm import tqdm
from langchain.text_splitter import RecursiveCharacterTextSplitter


import pyperclip
import tiktoken

def count_tokens_from_clipboard() -> int:
    # Get text from clipboard
    clipboard_content = pyperclip.paste()
    
    if not clipboard_content:
        print("Clipboard is empty.")
        return 0
    
    # Initialize tokenizer
    encoding = tiktoken.get_encoding("cl100k_base")  # Use appropriate model encoding here
    
    # Encode text to tokens
    tokens = encoding.encode(clipboard_content)
    
    # Return the number of tokens
    return len(tokens)

# Generator function to load embedding data file by file
def load_embedding_data(db_dir: str) -> Any:
    for filename in os.listdir(db_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(db_dir, filename)
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                yield json.load(f)['data']

def get_number_of_tokens(text: str) -> int:
    enc = tiktoken.get_encoding('cl100k_base')
    return len(enc.encode(text))



# Compute total tokens for a single file's data
def compute_tokens_for_file(data: List[Dict[str, Any]], chunk_size: int, chunk_overlap: int) -> int:
    total_tokens = 0
    
    for entry in tqdm(data, desc="Processing entries", leave=False):
        name = entry.get('name', '')
        introduction = entry.get('detail', {}).get('introduction', '')
        description = entry.get('detail', {}).get('description', '')
        
        # Calculate tokens for name and introduction
        total_tokens += get_number_of_tokens(name)
        total_tokens += get_number_of_tokens(introduction)
        
        # Calculate tokens for chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = text_splitter.split_text(description)
        
        for chunk in chunks:
            total_tokens += get_number_of_tokens(chunk)
    
    return total_tokens

def calculate_cost(total_tokens: int, small_token_threshold: int = 1000) -> float:
    price_per_token_small = 0.00000002
    price_per_token_large = 0.00000013
    return {"small": total_tokens * price_per_token_small, "large": total_tokens * price_per_token_large}

if __name__ == "__main__":
    tokens = count_tokens_from_clipboard()
    cost = calculate_cost(tokens)
    print(cost)
    print(tokens)
