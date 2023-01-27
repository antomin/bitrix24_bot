import logging
import time
from datetime import datetime
from random import choice

import requests
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from seleniumwire import webdriver

from settings import (BASE_DIR, CHAT_ID, HEADLESS, PASSWORD, TG_TOKEN,
                      USE_PROXY, USERNAME)

URL = 'https://bpmc.bitrix24.pl'

with open(f'{BASE_DIR}/old_offers.txt', 'r', encoding='utf-8') as file:
    old_offers = file.read().splitlines()


logging.basicConfig(level=logging.INFO)


def send_to_telegram(message):
    url = '\nhttps://bpmc.bitrix24.pl/marketplace/app/1/'
    requests.get(f'https://api.telegram.org/bot{TG_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message + url}')


def write_to_file(offer_id):
    with open(f'{BASE_DIR}/old_offers.txt', 'a', encoding='utf-8') as file:
        file.write(offer_id + '\n')


def get_rand_proxy():
    with open('proxy.txt', 'r') as f:
        proxy_list = f.read().splitlines()

    proxy = choice(proxy_list).split(':')

    return {'user': proxy[0], 'pass': proxy[1], 'host': proxy[2], 'port': int(proxy[3])}


# def connect_proxy(options):
#     proxy = get_rand_proxy()
#
#     manifest_json = """
#     {
#         "version": "1.0.0",
#         "manifest_version": 2,
#         "name": "Chrome Proxy",
#         "permissions": [
#             "proxy",
#             "tabs",
#             "unlimitedStorage",
#             "storage",
#             "<all_urls>",
#             "webRequest",
#             "webRequestBlocking"
#         ],
#         "background": {
#             "scripts": ["background.js"]
#         },
#         "minimum_chrome_version":"22.0.0"
#     }
#     """
#
#     background_js = """
#     var config = {
#             mode: "fixed_servers",
#             rules: {
#             singleProxy: {
#                 scheme: "http",
#                 host: "%s",
#                 port: parseInt(%s)
#             },
#             bypassList: ["localhost"]
#             }
#         };
#
#     chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});
#
#     function callbackFn(details) {
#         return {
#             authCredentials: {
#                 username: "%s",
#                 password: "%s"
#             }
#         };
#     }
#
#     chrome.webRequest.onAuthRequired.addListener(
#                 callbackFn,
#                 {urls: ["<all_urls>"]},
#                 ['blocking']
#     );
#     """ % (proxy['host'], proxy['port'], proxy['user'], proxy['pass'])
#
#     plugin = 'proxy_auth_plugin.zip'
#
#     with zipfile.ZipFile(plugin, 'w') as zp:
#         zp.writestr("manifest.json", manifest_json)
#         zp.writestr("background.js", background_js)
#
#     options.add_extension(plugin)
#
#     logging.info(f'Connected to {proxy["host"]}:{proxy["port"]}')
#
#     return options


def get_driver():
    options = webdriver.ChromeOptions()
    service = Service(f'{BASE_DIR}/drivers/chromedriver')

    if HEADLESS:
        options.add_argument('--headless=chrome')

    if USE_PROXY:
        proxy = get_rand_proxy()
        wire_options = {
            'proxy': {
                'http': f'http://{proxy["user"]}:{proxy["pass"]}@{proxy["host"]}:{proxy["port"]}',
                'https': f'https://{proxy["user"]}:{proxy["pass"]}@{proxy["host"]}:{proxy["port"]}',
                'no_proxy': 'localhost,127.0.0.1'
            }
        }

        return webdriver.Chrome(service=service, options=options, seleniumwire_options=wire_options)

    return webdriver.Chrome(service=service, options=options)


# def get_uc_driver():
#     options = undetected_chromedriver.ChromeOptions()
#     if USE_PROXY:
#         options = connect_proxy(options)
#     options.headless = HEADLESS
#     driver = undetected_chromedriver.Chrome(options=options,
#                                             driver_executable_path=f'{BASE_DIR}/drivers/undetected_chromedriver')
#
#     return driver


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
