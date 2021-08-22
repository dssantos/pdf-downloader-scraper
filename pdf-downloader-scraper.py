from time import sleep
from os import listdir
from os.path import dirname, abspath, getctime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import SessionNotCreatedException, WebDriverException, NoSuchElementException
from decouple import config, Csv
import pdfplumber

def last_file(download_path):
    '''Must return the filename of the most recent file in the folder'''
    files = [download_path + x for x in listdir(download_path) if x.endswith(".pdf")]
    newest = max(files , key = getctime)
    return newest

def pdf_downloader():
    '''Download file in especified folder after 
    scraping an element in headless mode and click on it'''
    try:
        # webdriver definitions
        download_path = dirname(abspath(__file__)) + '/downloads/'
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
        waiting_download = True
        atempt = 0
        while waiting_download:
            if atempt < 30:
                waiting_download = filename not in listdir(download_path)
                sleep(1)
                atempt += 1
            else:
                return 'Error', '', f'Time out. Download error after {atempt} atempts'
        print(f'File {filename} downloaded')
        driver.close()

    except (
        AttributeError,
        SessionNotCreatedException, 
        WebDriverException, 
        NoSuchElementException) as e:
        return 'Error', '', e

    return 'Success', filename, ''

def pdf_scraper(file_path):
    '''Must return a raw text of the PDF file'''
    file_path = dirname(abspath(__file__)) + '/downloads/diario_000548_20210820.pdf'
    pdf = pdfplumber.open(file_path)
    texts = []
    for num in range(len(pdf.pages)):
        page = pdf.pages[num]
        l_page = page.crop((0, 0.1 * float(page.height), 0.5 * float(page.width), 0.93 * float(page.height)))
        texts.append(l_page.extract_text())
        r_page = page.crop((0.5 * float(page.width), 0.1 * float(page.height), page.width, 0.93 * float(page.height)))
        texts.append(r_page.extract_text())
    text = '\n'.join(texts)
    return text

def send_mail(receiver_email, subject, msg):
    '''Sends a personalized message to specified email list'''
    return 'done'


email_list = config('EMAIL_LIST', cast=Csv())
status, filename, message_error = pdf_downloader()
if status == 'Success':
    file_path = dirname(abspath(__file__)) + '/downloads/' + filename
    pdf_content = pdf_scraper(file_path)
    text_list = config('TEXT_LIST', cast=Csv())
    raw_text = pdf_content.lower().replace('  ', ' ').replace('\n', ' ')
    if any(text_to_find.lower() in raw_text for text_to_find in text_list):
        for text_to_find in text_list:
            if text_to_find.lower() in raw_text:
                msg = f'{text_to_find} found in {filename}'
                send_mail(email_list, 'New updates', msg)
                print(f'Sending mail: {msg} to {", ".join(email_list)}')
    else:
        print('Texts not found:\n'+"\n".join(text_list))
else:
    send_mail(email_list, 'Error', message_error)
    print(f'Sending mail with error details:\n{message_error}')
