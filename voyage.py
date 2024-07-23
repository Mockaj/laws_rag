import voyageai
import json
from dotenv import load_dotenv
from tqdm import tqdm
import numpy as np
import os
load_dotenv()

vo = voyageai.Client()


def embed(text, input_type="document"):
    result = vo.embed(text, model="voyage-multilingual-2", input_type=input_type)
    return result.embeddings[0]

def rerank(query, documents, top_k=3):
    reranking_object = vo.rerank(query, documents, model="rerank-1", top_k=top_k)
    print(reranking_object)
    return reranking_object.results

def tokenize(texts):
    return vo.tokenize(texts)

def count_tokens(texts):
    return vo.count_tokens(texts)

def load_from_json(filename):
    return json.load(open(filename, 'r', encoding='utf-8-sig'))


def save_to_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f)


def run():
    embeddings_dict = {}
    data = load_from_json('laws_chunked.json')
    for key in tqdm(data, desc="Processing keys"):
        embeddings_dict[key] = {}
        for sub_key in tqdm(data[key], desc=f"Processing sub-keys of {key}"):
            embeddings_dict[key][sub_key] = {}
            text = data[key][sub_key]
            for i, chunk in enumerate(text):
                embedding = embed(chunk)
                embeddings_dict[key][sub_key][i] = embedding
    save_to_json(embeddings_dict, 'embeddings_voyage_law.json')


if __name__ == '__main__':
    run()
