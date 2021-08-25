from time import sleep
from os import listdir
from os.path import dirname, abspath, getctime
from pathlib import Path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from selenium import webdriver
from selenium.common import exceptions
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
        Path(download_path).mkdir(parents=True, exist_ok=True)
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
    pdf = pdfplumber.open(file_path)
    texts = []
    for num in range(len(pdf.pages)):
        page = pdf.pages[num]
        l_page = page.crop((0, 0.1 * float(page.height), 0.5 * float(page.width), 0.93 * float(page.height)))
        l_page_text = l_page.extract_text()
        if l_page_text is not None:
            texts.append(l_page_text)
        r_page = page.crop((0.5 * float(page.width), 0.1 * float(page.height), page.width, 0.93 * float(page.height)))
        r_page_text = r_page.extract_text()
        if r_page_text is not None:
            texts.append(r_page_text)
    text = '\n'.join(texts)
    return text

def send_mail(email_list, subject, content):
    '''Sends a personalized message to specified email list'''
    try:
        # Create message container - the correct MIME type is multipart/alternative.
        sender = f'{config("EMAIL_SENDER_NAME")} <{config("EMAIL_SENDER")}>'
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender    # Format: 'Name <user@mail.com>'
        msg['To'] = ", ".join(email_list)

        # Create the body of the message (a plain-text and an HTML version).
        text = content
        url = config('URL')
        html = f'''
        <html>
        <head></head>
        <body>
            {text}
            Last update: <a href="{url}">{url}</a>
        </body>
        </html>
        '''.replace("\n", "</br>")

        # Record the MIME types of both parts - text/plain and text/html.
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')

        # Attach parts into message container.
        # According to RFC 2046, the last part of a multipart message, in this case
        # the HTML message, is best and preferred.
        msg.attach(part1)
        msg.attach(part2)

        # Send the message via local SMTP server.
        server = smtplib.SMTP_SSL(config('EMAIL_HOST'), config('EMAIL_PORT', cast=int))
        server.ehlo()
        server.login('apikey', config('SENDGRID_API_KEY'))
        # sendmail function takes 3 arguments: sender's address, recipient's address
        # and message to send - here it is sent as one string.
        server.sendmail(sender, email_list, msg.as_string())
        server.quit()
    except Exception as e:
        print(e)

def main():
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
                    send_mail(email_list, f'{config("EMAIL_SUBJECT")} {config("SITE_NAME")}', msg)
                    print(f'Sending mail: {msg} to {", ".join(email_list)}')
        else:
            print('Texts not found:\n'+"\n".join(text_list))
    else:
        send_mail(email_list, f'Error {config("SITE_NAME")}', message_error)
        print(f'Sending mail with error details:\n{message_error}')

if __name__ == "__main__":
    main()
