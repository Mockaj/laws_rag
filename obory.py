from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import InvalidArgumentException, WebDriverException, NoSuchElementException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from pydantic import BaseModel
from time import sleep
from typing import List, Dict
from datetime import datetime
import json
import logging
import os

# Set up Selenium WebDriver
options = webdriver.ChromeOptions()
options.add_argument("--window-size=1080,1920")
options.add_argument("--disable-extensions")
options.add_argument("--proxy-server='direct://'")
options.add_argument("--proxy-bypass-list=*")
options.add_argument("--start-maximized")
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--no-sandbox')
options.add_argument('--ignore-certificate-errors')


logging.basicConfig(
    filename='logs.log',  # Log file path
    filemode='a',            # Append to the log file on each run
    format='%(asctime)s - %(levelname)s - %(message)s'  # Log message format
)


class LawDetail(BaseModel):
    introduction: str
    description: str


class Law(BaseModel):
    name: str
    effect: str
    link: str
    detail: LawDetail


def log_to_file(message):
    log_directory = 'logs'
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)
    log_file_path = os.path.join(log_directory, 'logs_zpl_v2.log')
    with open(log_file_path, 'a') as file:
        file.write(message + '\n')


count_requests = 0


def fetch_data():
    driver = webdriver.Chrome(service=Service(
        ChromeDriverManager().install()), options=options)
    obory = ['koronavirus']
    try:
        for obor in obory:
            count_requests = 0
            data = []
            driver.get(f'https://www.zakonyprolidi.cz/obor/{obor}')
            driver.execute_script("__doPostBack('X$idBody$Grid', 'SIZE200');")
            sleep(3)  # Wait for the page and JavaScript to fully load
            table_selector = '#Main > div.pg-body > div.PageMain > div > div.ContentBody > div.Paper > div.PdMain > table > tbody'

            for i in range(len(driver.find_elements(By.CSS_SELECTOR, f"{table_selector} tr"))):
                tr_elements = driver.find_elements(
                    By.CSS_SELECTOR, f"{table_selector} tr")
                tr = tr_elements[i]

                anchor_element = tr.find_element(By.CSS_SELECTOR, "td.c1 > a")
                link = anchor_element.get_attribute("href")
                name = tr.find_element(By.CSS_SELECTOR, "td.c2").text
                effect = tr.find_element(By.CSS_SELECTOR, "td.c3").text

                driver.get(link)
                sleep(1)

                elements = driver.find_elements(
                    By.XPATH, "//*[@id='idBody_idCtn']/div[@class='Frags']//*")
                introduction = '\n'.join(
                    [element.text for element in elements[:12]])
                description = '\n'.join(
                    [element.text for element in elements[12:] if element.tag_name.lower() != 'h4'])

                law_detail = LawDetail(
                    introduction=introduction, description=description)
                law = Law(name=name, effect=effect,
                          link=link, detail=law_detail)
                now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                law_intro_stripped = law.detail.introduction.replace('\n', '')
                log_message = f"{now} - Field: {obor.capitalize()}, Processed law: {law.name}, Link: {law.link}, Intro: {law_intro_stripped}"
                log_to_file(log_message)
                data.append(law)
                driver.back()
                sleep(1)
                count_requests += 3
            save_data_to_json(data, f'{obor}.json')
            print(count_requests)
    except Exception as e:
        print(f"Unexpected error occurred: {str(e)}")
    finally:
        driver.quit()


def save_data_to_json(data: List[Law], filename: str):
    directory = 'data'
    if not os.path.exists(directory):
        os.makedirs(directory)
    filepath = os.path.join(directory, filename)
    data_to_save = {"data": [law.dict() for law in data]}
    with open(filepath, 'w', encoding='utf-8-sig') as file:
        json.dump(data_to_save, file, ensure_ascii=False,
                  indent=4, default=str)


if __name__ == "__main__":
    fetch_data()
