from time import sleep
from os.path import dirname, abspath
import traceback

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import SessionNotCreatedException, WebDriverException, NoSuchElementException
from decouple import config, Csv

def last_file():
    '''Must return the filename of the most recent file in the folder'''
    return 'filename'

def pdf_downloader():
    '''Download file in especified folder after 
    scraping an element in headless mode and click on it'''
    try:
        # webdriver definitions
        download_path = dirname(abspath(__file__)) + '/downloads'
        prefs = {"download.default_directory":download_path}
        options = webdriver.ChromeOptions()
        options.binary_location = '/usr/bin/google-chrome'
        options.add_argument('headless')
        options.add_argument('window-size=1200x600')
        options.add_experimental_option("prefs", prefs)
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(30)

        # Open browser on url
        driver.get(config('URL'))
        print(driver.title.encode('utf8', 'replace'))

        # find date element
        date_xpath = '//*[@id="table_id"]/tbody/tr[1]/td[1]/a'
        date_element = driver.find_element(By.XPATH, date_xpath)
        date = date_element.text
        date = date[-4:]+date[3:5]+date[0:2]

        # find number element
        number_xpath = '//*[@id="table_id"]/tbody/tr[1]/td[2]'
        number_element = driver.find_element(By.XPATH, number_xpath)
        number = number_element.text

        # find download element and click
        download_xpath = '//*[@id="table_id"]/tbody/tr[1]/td[3]/a'
        download_element = driver.find_element(By.XPATH, download_xpath)
        download_element.click()

        # wait download finish and close browser
        filename = f'diario_{number}_{date}.pdf'
        for atempt in range(1,6):
            if filename is not last_file():
                sleep(2)
            else:
                return 'Error', '', f'Time out. Download error after {atempt} atempts'
        print(f'File {filename} downloaded')
        driver.close()

    except (
        SessionNotCreatedException, 
        WebDriverException, 
        NoSuchElementException) as e:
        return 'Error', '', e

    return 'Success', filename, ''
    

def read_pdf(filename):
    '''Must return a file object from a filename'''
    return 'file object'

def pdf_scraper(pdf_file):
    '''Must return a raw text of the PDF file'''
    return 'raw text'

def send_mail(receiver_email, subject, msg):
    '''Sends a personalized message to specified email list'''
    return 'done'


email_list = config('EMAIL_LIST', cast=Csv())
status, filename, message_error = pdf_downloader()
if status == 'Success':
    pdf_file = read_pdf(filename)
    pdf_content = pdf_scraper(pdf_file)
    text_list = config('TEXT_LIST', cast=Csv())
    if any(text_to_find.lower() in pdf_content.lower() for text_to_find in text_list):
        for text_to_find in text_list:
            if text_to_find.lower() in pdf_content.lower():
                msg = f'{text_to_find} found in {filename}'
                send_mail(email_list, 'New updates', msg)
                print(f'Sending {msg} to {", ".join(email_list)}')
    else:
        print('Texts not found:\n'+"\n".join(text_list))
else:
    send_mail(email_list, 'Error', message_error)
    print(f'Sending mail with error details:\n{message_error}')
