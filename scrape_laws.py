from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import InvalidArgumentException, WebDriverException
from time import sleep
import json
import logging


# Set up Selenium WebDriver
options = webdriver.ChromeOptions()
options.add_argument("--window-size=1920,1080")
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


def log_to_file(message):
    with open('logs.log', 'a') as file:
        file.write(message + '\n')


def fetch_data(year):
    driver = webdriver.Chrome(service=Service(
        ChromeDriverManager().install()), options=options)
    prefixes = ['sb', 'sm', 'ul0', 'ul1', 'ul2', 'ul3']
    suffixes = ['', 'n']
    # Ensure that the data dictionary for the year is initialized
    data = {year: {}}

    try:
        driver = webdriver.Chrome(service=Service(
            ChromeDriverManager().install()), options=options)  # ensure driver is defined
        for prefix in prefixes:
            for suffix in suffixes:
                for i in range(1, 10000):
                    url = f'https://www.e-sbirka.cz/{prefix}/{year}/{suffix+str(i)}'
                    driver.get(url)
                    sleep(2)

                    text_elements = driver.find_elements(
                        By.XPATH, '/html/body/esel-app/esel-app-main/div/main/esel-detail-predpisu-page/div/div/esel-left-or-slide-panel/div/main/esel-text-predpisu/div/div/esel-fragment-view/div')
                    text_content = ' '.join(
                        [element.text for element in text_elements])
                    if text_elements == []:
                        log_to_file(
                            f'ending run for {prefix}/{year}/{suffix+str(i)}')
                        break
                    data[year][f'{prefix}/{year}/{suffix+str(i)}'] = text_content
                    log_to_file(
                        f'{prefix}/{year}/{suffix+str(i)}')
    except Exception as e:
        print(f"Unexpected error occurred: {str(e)}")
    finally:
        driver.quit()
        return data


def save_data_to_json(data: dict):
    with open(f'laws.jsonl', 'a', encoding='utf-8-sig') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    data = {}
    for year in range(1948, 2025):
        print("starting year: ", year)
        data = fetch_data(year)
        save_data_to_json(data)
