import json
import os
import re
import requests
from urllib.parse import quote
from typing import Any, List
from pymongo import MongoClient
from pydantic import BaseModel, ValidationError

# Define your data models
class Paragraf(BaseModel):
    cislo: str
    zneni: str
    law_name: str
    year: str
    isValid: bool = True  # Add isValid field with default value True

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
                "year": law.year,
                "staleURL": law.staleURL,
                "isValid": paragraf.isValid
            }
            collection.update_one(
                {"cislo": paragraf.cislo, "law_name": law.nazev, "year": law.year, "staleURL": law.staleURL},
                {"$set": paragraf_doc})
            print(f"Paragraph {paragraf.cislo} from law '{law.nazev}' updated to collection '{data.field}'.")

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

# Function to validate records using the API
def validate_records(db_name="law_database"):
    client = get_mongo_client()
    db = client[db_name]
    
    collections = db.list_collection_names()
    headers = {"esel-api-access-key": "0zIAcHQyAcqhlxxExaJqjsAeiZaocXgVKifkIAtuuzqgtmwgclGDCQbtsyovsBIij"}
    processed_staleURLs = set()  # Set to keep track of checked staleURLs

    for collection_name in collections:
        collection = db[collection_name]
        valid_records = collection.find({"isValid": True})

        for record in valid_records:
            staleURL = record['staleURL']

            if staleURL in processed_staleURLs:
                continue  # Skip this record if the staleURL was already checked

            encoded_staleURL = quote(staleURL, safe='')  # Encode the staleURL
            api_url = f"https://api.e-sbirka.cz/dokumenty-sbirky/{encoded_staleURL}/souvislosti"
            
            response = requests.get(api_url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                for item in data['souvislosti']:
                    if item['typ'] == "UPLNA_ZNENI_REPUBLIKOVAN":
                        for doc in item['dokumentySbirky']:
                            if doc['stavDokumentuSbirky'] == "ZRUSENY":
                              collection.update_many({"staleURL": staleURL}, {"$set": {"isValid": False}})
                              print(f"Updated isValid to False for records with staleURL: {staleURL}")

                # Mark this staleURL as processed
                processed_staleURLs.add(staleURL)
            else:
                print(f"Failed to fetch data from API for staleURL: {staleURL}")

if __name__ == '__main__':
    validate_records()  # Validate records using the API
