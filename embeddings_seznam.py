from transformers import AutoModel, AutoTokenizer
import json
from tqdm import tqdm
import numpy as np

def load_from_json(filename):
    return json.load(open(filename, 'r', encoding='utf-8-sig'))


def save_to_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f)


model_name = "Seznam/retromae-small-cs"  # Hugging Face link
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)

data_text = load_from_json('laws.json')
# embeddings_dict = {}

# for key in tqdm(data, desc="Processing keys"):
#     embeddings_dict[key] = {}
#     for sub_key in tqdm(data[key], desc=f"Processing sub-keys of {key}"):
#         batch_dict = tokenizer(data[key][sub_key], max_length=512,
#                                padding=True, truncation=True, return_tensors='pt')
#         outputs = model(**batch_dict)
#         embeddings = outputs.last_hidden_state[:, 0][0]
#         embeddings_dict[key][sub_key] = embeddings.tolist()


# save_to_json(embeddings_dict, 'embeddings_seznam.json')

results = []
query = 'Napiš mi, v jakém předpise a paragrafu je upravena výpověď a jaká je dle českého práva výpovědní doba.'
query_dict = tokenizer(query, max_length=512,
                               padding=True, truncation=True, return_tensors='pt')
outputs = model(**query_dict)
embedded_query = outputs.last_hidden_state[:, 0][0]
embedded_query_tra = embedded_query.detach().numpy().T
data_emb = load_from_json('embeddings_seznam.json')
for key_emb, key_text in zip(data_emb, data_text):
    for sub_emb, sub_text in zip(data_emb[key_emb], data_text[key_text]):
        score = (np.array(data_emb[key_emb][sub_emb]) @ embedded_query_tra) / (np.linalg.norm(np.array(data_emb[key_emb][sub_emb])) * np.linalg.norm(embedded_query.detach().numpy()))
        results.append((score, data_text[key_text][sub_text], sub_text))

sorted_results = sorted(results, key=lambda x: x[0], reverse=True)

# Optionally, to see or use the sorted results:
for score, text, mark in sorted_results[:10]:
    print(f'Score: {score:.5f}, mark: {mark}')  