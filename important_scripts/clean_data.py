import requests
import json
import os
import re
from typing import Any, List
from pydantic import BaseModel
from pymongo import MongoClient
from datetime import datetime

class Paragraf(BaseModel):
    cislo: str
    zneni: str
    staleURL: str
    isValid: bool
    law_name: str

class Law(BaseModel):
    nazev: str
    staleURL: str
    paragrafy: List[Paragraf]

class Laws(BaseModel):
    field: str
    laws: List[Law]

def save_paragraphs_to_mongodb(paragraphs: List[Paragraf], collection_name: str, db_name="law_database"):
    client = MongoClient("mongodb://localhost:27017/")
    db = client[db_name]
    collection = db[collection_name + "_v2"]
    for paragraf in paragraphs:
        collection.update_one(
            {"staleURL": paragraf.staleURL, "cislo": paragraf.cislo},
            {"$set": paragraf.model_dump()},
            upsert=True
        )

def load_from_json(filename: str) -> Any:
    with open(filename, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    return data['data']

def get_laws(dir_name: str):
    num_pattern = r'\d+'
    text_pattern = r'<[^>]+>'
    headers = {"esel-api-access-key": "0zIAcHQyAcqhlxxExaJqjsAeiZaocXgVKifkIAtuuzqgtmwgclGDCQbtsyovsBIij"}
    files = os.listdir("../data")
    for file_num, file in enumerate(files):
        data = load_from_json(f"../data/{file}")
        field = file.removesuffix(".json")
        paragraphs = []
        for law_num, law_data in enumerate(data):
            print(f"processing {file_num+1}/{len(files)}: {law_num+1}/{len(data)}", end="\r")
            sign = law_data['link']
            val = sign.split('/')[-1]
            sign = val.split('-')
            sign = "%2Fsb%2F"+sign[0]+"%2F"+sign[1]+"%2F0000-00-00"
            try:
                res = requests.get("https://api.e-sbirka.cz/dokumenty-sbirky/"+sign, headers=headers).json()
            except Exception as e:
                print(f"Failed to fetch law details for {sign}")
                continue
            if res.get('nazev') is None:
                continue
            nazev = res['nazev']
            staleURL = res['staleUrl']
            datumZruseni = res.get('datumZruseni')
            is_valid = datumZruseni is None or datetime.strptime(datumZruseni, "%Y-%m-%d") > datetime.now()
            for i in range(50):
                response = requests.get("https://api.e-sbirka.cz/dokumenty-sbirky/"+sign+"/fragmenty?cisloStranky="+str(i), headers=headers).json()
                if response.get('chyby') is not None:
                    break
                fragments = response['seznam']
                current_paragraph_number = None
                current_paragraph_text = ""
                for fragment in fragments:
                    if fragment['kodTypuFragmentu'] == 'Paragraf':
                        if current_paragraph_number is not None:
                            # Save the current paragraph before starting a new one
                            paragraphs.append(Paragraf(
                                cislo=current_paragraph_number,
                                zneni=current_paragraph_text.strip(),
                                staleURL=staleURL,
                                isValid=is_valid,
                                law_name=nazev
                            ))
                        # Start a new paragraph
                        match = re.search(num_pattern, fragment['xhtml'])
                        if match is None:
                            raise ValueError("Paragraf number not found")
                        current_paragraph_number = match.group()
                        current_paragraph_text = ""
                    else:
                        # Append fragment text to the current paragraph
                        cleaned_text = re.sub(text_pattern, '', fragment.get('xhtml', ''))
                        current_paragraph_text += cleaned_text + "\n"
                # Save the last paragraph if it exists
                if current_paragraph_number is not None:
                    paragraphs.append(Paragraf(
                        cislo=current_paragraph_number,
                        zneni=current_paragraph_text.strip(),
                        staleURL=staleURL,
                        isValid=is_valid,
                        law_name=nazev
                    ))
        save_paragraphs_to_mongodb(paragraphs, field)

if __name__ == '__main__':
    output_dir = "../open_data/laws"
    get_laws(output_dir)
