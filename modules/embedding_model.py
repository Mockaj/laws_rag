from typing import List
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel
from dotenv import load_dotenv
import os
import torch
# Load environment variables from the .env file
load_dotenv()

# Retrieve the Hugging Face token from the environment variable
token = os.getenv('HF_TOKEN')

# model = SentenceTransformer("nvidia/NV-Embed-v1")

# def get_embeddings(texts: List[str]):
#         return model.encode(texts)

import torch
import torch.nn.functional as F
from torch import Tensor
from transformers import AutoTokenizer, AutoModel
from typing import List

# Check if MPS (Metal Performance Shaders) is available
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

# Load model with tokenizer
model = AutoModel.from_pretrained('Linq-AI-Research/Linq-Embed-Mistral', trust_remote_code=True)

# Convert the model to FP16
model = model.to(dtype=torch.float16, device=device)

# Load the tokenizer
tokenizer = AutoTokenizer.from_pretrained('Linq-AI-Research/Linq-Embed-Mistral', trust_remote_code=True)

# Define the max length for inputs
max_length = 4096

def get_embeddings(texts: List[str]):
    # Tokenize the input texts
    inputs = tokenizer(texts, padding=True, truncation=True, return_tensors="pt", max_length=max_length)
    
    # Manually move each tensor to the correct device
    input_ids = inputs['input_ids'].to(device)
    
    # Convert attention_mask and token_type_ids to float16 and move to device if they exist
    attention_mask = inputs['attention_mask'].to(device) if 'attention_mask' in inputs else None
    token_type_ids = inputs['token_type_ids'].to(device) if 'token_type_ids' in inputs else None
    
    with torch.no_grad():
        # Convert attention_mask and token_type_ids to float16
        if attention_mask is not None:
            attention_mask = attention_mask.to(dtype=torch.float16)
        if token_type_ids is not None:
            token_type_ids = token_type_ids.to(dtype=torch.float16)
        
        outputs = model(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids)
        embedding = outputs.last_hidden_state.mean(dim=1)  # Assuming mean pooling of the output embeddings
    
    return F.normalize(embedding.to(dtype=torch.float32), p=2, dim=1).tolist()  # Normalize in FP32





