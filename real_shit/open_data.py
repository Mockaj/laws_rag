import requests
import json
import os
import re
from typing import Any, List
from pydantic import BaseModel

class Paragraf(BaseModel):
    cislo: str
    zneni: str

class Law(BaseModel):
    nazev: str
    staleURL: str
    paragrafy: List[Paragraf]

class Laws(BaseModel):
    field: str
    laws: List[Law]

def save_data_to_json(data: Laws, filename: str):
    with open(f'{filename}', 'w', encoding='utf-8-sig') as file:
        json_string = json.dumps(data.model_dump(), ensure_ascii=False, indent=4)
        file.write(json_string)

def load_from_json(filename: str) -> Any:
    with open(filename, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    return data['data']

def get_laws(dir_name: str):
    num_pattern = r'\d+'
    text_pattern = r'<[^>]+>'
    headers = {"esel-api-access-key": "0zIAcHQyAcqhlxxExaJqjsAeiZaocXgVKifkIAtuuzqgtmwgclGDCQbtsyovsBIij"}
    files = os.listdir("data")
    for file_num, file in enumerate(files):
        data = load_from_json(f"data/{file}")
        field = file.removesuffix(".json")
        laws = Laws(field=field, laws=[])
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
            law = Law(nazev=nazev, staleURL=staleURL, paragrafy=[])
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
                            law.paragrafy.append(Paragraf(cislo=current_paragraph_number, zneni=current_paragraph_text.strip()))
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
                    law.paragrafy.append(Paragraf(cislo=current_paragraph_number, zneni=current_paragraph_text.strip()))
            laws.laws.append(law)
        save_data_to_json(laws, f"{dir_name}/{field}.json")
            

if __name__ == '__main__':
    output_dir = "open_data/laws"
    get_laws(output_dir)
