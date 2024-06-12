import contextlib
import logging
import time
from datetime import datetime
from random import choice

import requests
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from seleniumwire import webdriver

from settings import (BASE_DIR, CHAT_ID, HEADLESS, TG_TOKEN, USE_PROXY)

# URL = 'https://2ip.ru'
URL = 'https://bpmc.bitrix24.pl/marketplace/app/129/'

with open(f'{BASE_DIR}/old_offers.txt', 'r', encoding='utf-8') as file:
    old_offers = file.read().splitlines()

# logging
logging.basicConfig(level=logging.INFO, format='%(asctime)-30s %(levelname)-15s %(message)s',
                    filename=f'{BASE_DIR}/log/{datetime.now().strftime("%d-%m-%Y")}.log')
loger_selenium = logging.getLogger('seleniumwire')
loger_selenium.setLevel(logging.ERROR)


def send_to_telegram(message):
    url = f'\n{URL}'
    requests.get(f'https://api.telegram.org/bot{TG_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message + url}')


def write_to_file(offer_id):
    with open(f'{BASE_DIR}/old_offers.txt', 'a', encoding='utf-8') as file:
        file.write(offer_id + '\n')


def get_rand_proxy():
    with open(f'{BASE_DIR}/proxy.txt', 'r') as f:
        proxy_list = f.read().splitlines()

    return choice(proxy_list)


def get_rand_account():
    with open(f'{BASE_DIR}/accounts.txt', 'r') as f:
        accounts_list = f.read().splitlines()

    account = choice(accounts_list).split(':')

    return {'username': account[0], 'password': account[1]}


def get_driver():
    options = webdriver.ChromeOptions()
    options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})

    if HEADLESS:
        options.add_argument('--headless=chrome')

    if USE_PROXY:
        proxy = get_rand_proxy()
        wire_options = {
            'proxy': {
                'http': f'http://{proxy}',
                'https': f'https://{proxy}',
                'no_proxy': 'localhost,127.0.0.1'
            }
        }

        logging.info(f'Driver start with proxy {proxy}')
        driver = webdriver.Chrome(options=options, seleniumwire_options=wire_options)
        return driver

    logging.info('Driver start without proxy')
    return webdriver.Chrome(options=options)


def main():
    logging.info('Start parsing.')

    driver = get_driver()
    wait = WebDriverWait(driver, 60)
    account = get_rand_account()

    logging.info(f'Use account {account["username"]}')

    try:
        driver.get(URL)

        if HEADLESS:
            try:
                driver.find_element(By.XPATH, '//span[@class="popup-window-close-icon"]').click()
            except Exception:
                pass

        logging.info('Start authorization.')

        next_button = wait.until(EC.presence_of_element_located((By.XPATH, '//button[@data-action="submit"]')))
        wait.until(EC.presence_of_element_located((By.ID, 'login'))).send_keys(account['username'])
        # action.move_to_element(next_button).click(next_button).perform()
        time.sleep(1)
        next_button.click()
        time.sleep(1)

        next_button = wait.until(EC.presence_of_element_located((By.XPATH, '//button[@data-action="submit"]')))
        wait.until(EC.presence_of_element_located((By.ID, 'password'))).send_keys(account['password'])
        time.sleep(1)
        next_button.click()

        logging.info('Authorization is done.')
        logging.info('Waiting slots info.')

        frame_wrapper = wait.until(EC.presence_of_element_located((By.XPATH, '//iframe[@class="app-frame"]')))
        driver.switch_to.frame(frame_wrapper)
        frame_inner = wait.until(EC.presence_of_element_located((By.XPATH, '//iframe[@name="partner_application"]')))
        driver.switch_to.frame(frame_inner)

        # wait.until(EC.presence_of_element_located(
        #     (By.XPATH, '//div[@class="partner-application-b24-statistic-table-head-btn-inner"]'))).click()

        elems = wait.until(
            EC.presence_of_all_elements_located(
                (By.XPATH, '//tr[@class="main-grid-row main-grid-row-body"]')
            )
        )

        logging.info('Check slots.')

        for elem in elems:
            offer_id = elem.get_attribute('data-id')
            tds = elem.find_elements(By.XPATH, 'td[@class="main-grid-cell main-grid-cell-left"]')
            if tds[3].text != 'No vacant slots' and offer_id not in old_offers:
                send_to_telegram(f'FREE_SLOT ID {offer_id}.')
                logging.info('Found slots.')
                write_to_file(offer_id)

        logging.info('No free slots.')

    except Exception as error:
        driver.get_screenshot_as_file(f'{BASE_DIR}/screen.png')
        logging.error(f'ERROR with parsing: {error}')

    finally:
        driver.close()
        driver.quit()
        logging.info('Finish parsing without errors.')


if __name__ == '__main__':
    main()
