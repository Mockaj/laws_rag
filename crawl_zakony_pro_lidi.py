from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import InvalidArgumentException, WebDriverException, NoSuchElementException
from time import sleep
import json
import logging


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


def log_to_file(message):
    with open('logs_zpl.log', 'a') as file:
        file.write(message + '\n')


def fetch_data():
    driver = webdriver.Chrome(service=Service(
        ChromeDriverManager().install()), options=options)
    courts = {"nejvyssi_soud": 1,
              "nejvyssi_spravni_soud": 2, "ustavni_soud": 3}
    try:
        driver = webdriver.Chrome(service=Service(
            ChromeDriverManager().install()), options=options)
        for court in courts:
            button_selector = '#Main > div.pg-body > div.PageMain > div > div.ContentBody > div.Paper > div.grid-body > div.grid-main > div.grid-footer > div > a.btn.btn-secondary.command.next'
            data = {}
            url = f'https://www.zakonyprolidi.cz/judikaty-hledani?a={courts[court]}&to=2021-05-27'
            driver.get(url)
            sleep(1)
            while True:
                try:
                    link_elements = driver.find_elements(
                        By.CSS_SELECTOR, '.ResultList .Item.Jud a.dos')
                    links = []
                    for link in link_elements:
                        links.append(link.get_attribute('href'))
                    for link in links:
                        print(link)
                        driver.get(link)
                        sleep(0.1)
                        div_element = driver.find_element(
                            By.XPATH, '//*[@id="idBody_idCtn"]')
                        div_text = div_element.text
                        parts = link.split("/")
                        last_part = parts[-1]
                        data[last_part] = div_text
                        driver.back()
                        sleep(0.1)
                    sleep(0.5)
                    element = driver.find_element(
                        By.CSS_SELECTOR, button_selector)
                    class_name = element.get_attribute("class")
                    if "disabled" in class_name:
                        raise NoSuchElementException
                    driver.execute_script("arguments[0].click();", element)
                    sleep(1)
                except NoSuchElementException:
                    log_to_file("Ending for court "+court)
                    save_data_to_json(data, court+"_rozhodnuti.json")
                    break

    except Exception as e:
        print(f"Unexpected error occurred: {str(e)}")
    finally:
        driver.quit()


def save_data_to_json(data: dict, filename: str):
    with open(f'{filename}', 'w', encoding='utf-8-sig') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    fetch_data()
