import openai
import os
import json
from dotenv import load_dotenv
from tqdm import tqdm
import numpy as np
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = openai.Client(api_key=api_key)


def embed_small(text):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def embed_large(text):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-large"
    )
    return response.data[0].embedding

def load_from_json(filename):
    return json.load(open(filename, 'r', encoding='utf-8-sig'))


def save_to_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f)


# def run():
#     results = []
#     query = "V jakém předpise a paragrafu je upravena výpověď pracovního poměru a jaká je dle českého práva výpovědní doba."
#     embedded_query = np.array(embed(query)).T
#     data_text = load_from_json('laws_chunked.json')
#     data_emb = load_from_json('embeddings_openai_small.json')
#     for key_emb, key_text in tqdm(zip(data_emb, data_text)):
#         for sub_emb, sub_text in tqdm(zip(data_emb[key_emb], data_text[key_text])):
#             for chunk_text, chunk_emb in tqdm(zip(data_text[key_text][sub_text], data_emb[key_emb][sub_emb])):
#                 score = np.array(
#                     data_emb[key_emb][sub_emb][chunk_emb]) @ embedded_query
#                 results.append((score, sub_text, chunk_text))
#     sorted_results = sorted(results, key=lambda x: x[0], reverse=True)
#     return sorted_results


def main():
    pass


if __name__ == '__main__':
    print(embed_small("This is a test."))