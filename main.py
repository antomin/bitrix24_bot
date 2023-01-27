import logging
import time
import zipfile
from datetime import datetime

import requests
import undetected_chromedriver
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from settings import BASE_DIR, CHAT_ID, HEADLESS, PASSWORD, TG_TOKEN, USERNAME

URL = 'https://bpmc.bitrix24.pl'

with open(f'{BASE_DIR}/old_offers.txt', 'r', encoding='utf-8') as file:
    old_offers = file.read().splitlines()


logging.basicConfig(filename=f'{BASE_DIR}/log/{datetime.now().date()}.log', level=logging.INFO)


def send_to_telegram(message):
    url = '\nhttps://bpmc.bitrix24.pl/marketplace/app/1/'
    requests.get(f'https://api.telegram.org/bot{TG_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message + url}')


def write_to_file(offer_id):
    with open(f'{BASE_DIR}/old_offers.txt', 'a', encoding='utf-8') as file:
        file.write(offer_id + '\n')


def get_uc_driver():
    options = undetected_chromedriver.ChromeOptions()
    options.headless = HEADLESS
    driver = undetected_chromedriver.Chrome(options=options,
                                            driver_executable_path=f'{BASE_DIR}/drivers/undetected_chromedriver')

    return driver


def get_driver():
    options = webdriver.ChromeOptions()
    options.headless = HEADLESS
    service = Service(f'{BASE_DIR}/drivers/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)

    return driver


def main():
    logging.info('Start parsing.')

    driver = get_driver()
    wait = WebDriverWait(driver, 20)
    action = ActionChains(driver)

    try:
        driver.get(URL)

        if HEADLESS:
            try:
                driver.find_element(By.XPATH, '//span[@class="popup-window-close-icon"]').click()
            except Exception:
                pass

        next_button = wait.until(EC.presence_of_element_located((By.XPATH, '//button[@data-action="submit"]')))
        wait.until(EC.presence_of_element_located((By.ID, 'login'))).send_keys(USERNAME)
        action.move_to_element(next_button).click(next_button).perform()

        time.sleep(1)

        next_button = wait.until(EC.presence_of_element_located((By.XPATH, '//button[@data-action="submit"]')))
        wait.until(EC.presence_of_element_located((By.ID, 'password'))).send_keys(PASSWORD)
        action.move_to_element(next_button).click(next_button).perform()

        logging.info('Authorization is done.')

        frame_wrapper = wait.until(EC.presence_of_element_located((By.XPATH, '//iframe[@class="app-frame"]')))
        driver.switch_to.frame(frame_wrapper)
        frame_inner = wait.until(EC.presence_of_element_located((By.XPATH, '//iframe[@name="partner_application"]')))
        driver.switch_to.frame(frame_inner)

        wait.until(EC.presence_of_element_located(
            (By.XPATH, '//div[@class="partner-application-b24-statistic-table-head-btn-inner"]'))).click()

        elems = wait.until(
            EC.presence_of_all_elements_located(
                (By.XPATH, '//tr[@class="main-grid-row main-grid-row-body"]')
            )
        )

        for elem in elems:
            offer_id = elem.get_attribute('data-id')
            tds = elem.find_elements(By.XPATH, 'td[@class="main-grid-cell main-grid-cell-left"]')
            if tds[3].text != 'No vacant slots' and offer_id not in old_offers:
                send_to_telegram(f'FREE_SLOT ID {offer_id}.')
                logging.info('Found slots.')
                write_to_file(offer_id)

        logging.info('Finish parsing without errors.')

    except Exception as error:
        driver.get_screenshot_as_file(f'{BASE_DIR}/screen.png')
        logging.info(f'ERROR with parsing: {error}')
        send_to_telegram(f'ERROR: {error}')

    finally:
        driver.close()
        driver.quit()


if __name__ == '__main__':
    main()
