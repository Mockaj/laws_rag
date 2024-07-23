import json
import os
import re
import hashlib
from typing import Any, List
from pymongo import MongoClient
from pydantic import BaseModel, ValidationError

# Define your data models
class Paragraf(BaseModel):
    cislo: str
    zneni: str
    law_name: str
    year: str

class Law(BaseModel):
    nazev: str
    staleURL: str
    year: str
    paragrafy: List[Paragraf]

class Laws(BaseModel):
    field: str
    laws: List[Law]

# Connect to MongoDB
def get_mongo_client():
    client = MongoClient("mongodb://localhost:27017/")
    return client

# Wipe the database
def wipe_database(db_name="law_database"):
    client = get_mongo_client()
    client.drop_database(db_name)
    print(f"Database '{db_name}' wiped.")

# Function to extract the year from staleURL
def extract_year(staleURL: str) -> str:
    match = re.search(r'/(\d{4})/', staleURL)
    if match:
        return match.group(1)
    raise ValueError(f"Year not found in staleURL: {staleURL}")

# Save data to MongoDB with paragraphs as documents in collections named after the field
def save_data_to_mongodb(data: Laws, db_name="law_database"):
    client = get_mongo_client()
    db = client[db_name]
    
    collection = db[data.field]
    for law in data.laws:
        for paragraf in law.paragrafy:
            paragraf_doc = {
                "cislo": paragraf.cislo,
                "zneni": paragraf.zneni,
                "law_name": law.nazev,
                "year": law.year
            }
            collection.insert_one(paragraf_doc)
            print(f"Paragraph {paragraf.cislo} from law '{law.nazev}' saved to collection '{data.field}'.")

# Load data from JSON file and validate it against the Pydantic model
def load_from_json(filename: str) -> Laws:
    with open(filename, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    
    laws_list = []
    for law_data in data['laws']:
        try:
            year = extract_year(law_data['staleURL'])
            paragrafy = [Paragraf(**p, law_name=law_data['nazev'], year=year) for p in law_data['paragrafy']]
            law = Law(
                nazev=law_data['nazev'],
                staleURL=law_data['staleURL'],
                year=year,
                paragrafy=paragrafy
            )
            laws_list.append(law)
        except (ValidationError, ValueError) as e:
            print(f"Validation error for law data in file '{filename}': {e}")
    
    return Laws(field=data['field'], laws=laws_list)

# Function to process and save all JSON files in the specified directory to MongoDB
def process_and_save_json_files(dir_name: str):
    files = os.listdir(dir_name)
    for file in files:
        if file.endswith(".json"):
            print(f"Processing file: {file}")
            try:
                laws = load_from_json(os.path.join(dir_name, file))
                save_data_to_mongodb(laws)
                print(f"Finished processing file: {file}")
            except ValidationError as e:
                print(f"Validation error while processing file '{file}': {e}")

if __name__ == '__main__':
    output_dir = "../open_data/laws"  # Specify your output directory here
    wipe_database()  # Wipe the database before processing
    process_and_save_json_files(output_dir)
