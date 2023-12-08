import os
from selenium import webdriver
from time import sleep
from tqdm import tqdm
import pandas as pd
import requests
import json

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

api_headers = {
    "Accept": "application/json",
    "X-ELS-APIKey": "insert here"
}

ChromeDriverManager().install()
_pathfile = os.path.dirname(__file__)+"/temp"
def start_driver():
    chrome_options = webdriver.ChromeOptions();
    prefs = {"download.default_directory": _pathfile}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_experimental_option("excludeSwitches", ['enable-automation','enable-logging']);
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-dev-shm-usage')
    # chrome_options.add_argument('--app=data:')
    return webdriver.Chrome(options=chrome_options, service=ChromeService())

driver = None

# [EDIT] dataframe from input xlsx
df = pd.read_excel('sample.xlsx', dtype=str)

# [EDIT] section for XPATH element
elems = {
    'authId': '//*[@data-testid="authorId"]',
    'hindex': '//*[@data-testid="metrics-section-h-index"]',
    'export_document_1': '//*[@id="documents-panel"]/div/div/div[2]/div[2]/ul/li[1]/div/span/button',
    'export_document_2': '//*[@data-testid="export-to-csv"]',
    'export_document_3': '//*[@data-testid="submit-export-button"]',
    'export_cited_1': '//button[@id="cited-by"]',
    'export_cited_2': '//*[@id="cited-by-panel"]/div/div[2]/div[2]/div[2]/ul/li[1]/div/span/button',
    'export_cited_3': '//*[@data-testid="export-to-csv"]',
    'export_cited_4': '//*[@data-testid="submit-export-button"]',
    'export_download_1': '//input[@id="field_group_volumeIssuePages"]',
    'export_download_2': '//input[@id="field_group_sourceDocumentType"]',
    'export_download_3': '//input[@id="field_group_doi"]',
    'export_download_4': '//input[@id="field_group_openAccess"]',
    'export_close_modal': '//*[@data-testid="modal-dismiss"]',
}

def waitForElement(elem):
    result = EC.presence_of_element_located(elem)
    WebDriverWait(driver, 10).until(result)
# download fild and wait until complete
def downloadFileProcess(title="file", index=0, subindex=0, proc_1=(), proc_2=()):
    try:
        proc_1()

        # wait downloaded documents detail file and kept it to database
        clicked = False
        while clicked is False:
                sleep(1)
                try:
                    for download_index in range(1, 5):
                        waitForElement((By.XPATH, elems[f'export_download_{download_index}']))
                        driver.find_element(By.XPATH, elems[f'export_download_{download_index}']).click()
                    sleep(0.5)
                    while clicked is False:
                        proc_2()

                        try:
                            driver.find_element(By.XPATH, elems['export_close_modal'])
                        except NoSuchElementException:
                            clicked = True
                except:
                    break

        found_file = False
        while clicked is True and found_file is False:
            sleep(.5)
            if os.path.isfile(f'{_pathfile}/scopus.csv'):
                old_name = f'{_pathfile}/scopus.csv'
                new_name = f'{_pathfile}/{title}_{index}{"-"+subindex if subindex != 0 else ""}.csv'
                os.rename(old_name, new_name)
                found_file = True
                break
    except:
        pass

# -1 clear file in temp directory
for root, dirs, files in os.walk(_pathfile):
    for file in files:
        os.remove(os.path.join(root, file))

for index, row in tqdm(df.iterrows(), total=len(df), desc="Authors Processing"):
    row = row.copy()

    scopus_ids = str(row['Scopus ID']).split('; ')
    links = ['https://www.scopus.com/authid/detail.url?authorId=%s' %
            scopus_id for scopus_id in scopus_ids]
    api_links = ['https://api.elsevier.com/content/author/author_id/%s' %
            scopus_id for scopus_id in scopus_ids]

    NUM_PUBS = 0
    CITES = 0
    CITES_SELF = 0
    HINDEX = 0
    HINDEX_SELF = 0

    for i in range(0, len(links)):
        if scopus_ids[i] == "nan":
            continue

        if driver is None:
            driver = start_driver()
            # driver.set_window_position(2600, 0)


        api_link = api_links[i]
        link = links[i]
        scopus_id = scopus_ids[i]

        # 01 get prepared data from api (may un-used soon)
        api_response = requests.get(api_link, data=json.dumps(""), headers=api_headers)
        if api_response.status_code == 200:
            coredata = api_response.json()["author-retrieval-response"][0]["coredata"];
            NUM_PUBS += int(coredata['document-count'])
            CITES += int(coredata['cited-by-count'])
            CITES_SELF += int(coredata['citation-count'])

        driver.get(link)

        # wait elements in scopus loaded
        # waitForElement((By.XPATH, elems['authId']))

        # check id
        waitForElement((By.XPATH, elems['authId']))
        info = driver.find_element(By.XPATH, elems['authId'])
        info = info.text.strip()
        try:
            waitForElement((By.XPATH, elems['authId']))
            info = driver.find_element(By.XPATH, elems['authId'])
            info = info.text.strip()
        except:
            pass

        # 02 hindex (ok)
        # try:

        #     hindex = driver.find_element(By.XPATH, elems['hindex'])
        #     hindex = int(hindex.text.strip().split('\n')[0])

        #     if hindex > HINDEX:
        #         HINDEX = hindex

        # except:
        #     hindex = 0
        #     pass
        driver.execute_script('window.scrollBy(0,300)')

        # 03 load documents
        downloadFileProcess(title='docs', 
                            index=index, 
                            subindex=i,
                            proc_1=(
                                lambda: (
                                    waitForElement((By.XPATH, elems['export_document_1'])),
                                    driver.find_element(By.XPATH, elems['export_document_1']).click(),
                                    waitForElement((By.XPATH, elems['export_document_2'])),
                                    driver.find_element(By.XPATH, elems['export_document_2']).click()
                                )
                            ),
                            proc_2=(
                                lambda: (
                                    waitForElement((By.XPATH, elems['export_document_3'])),
                                    driver.find_element(By.XPATH, elems['export_document_3']).click(),
                                )
                            )
        )

        # 04 load citedby
        downloadFileProcess(title='cted', 
                            index=index, 
                            subindex=i,
                            proc_1=(
                                lambda: (
                                    waitForElement((By.XPATH, elems['export_cited_1'])),
                                    driver.find_element(By.XPATH, elems['export_cited_1']).click(),
                                    waitForElement((By.XPATH, elems['export_cited_2'])),
                                    driver.find_element(By.XPATH, elems['export_cited_2']).click(),
                                    waitForElement((By.XPATH, elems['export_cited_3'])),
                                    driver.find_element(By.XPATH, elems['export_cited_3']).click()
                                )
                            ),
                            proc_2=(
                                lambda: (
                                    waitForElement((By.XPATH, elems['export_cited_4'])),
                                    driver.find_element(By.XPATH, elems['export_cited_4']).click()
                                )
                            )
        )

        # throw a warning if the scopus link get redirect somewhere else
        if scopus_id != info:
            print('[WARN] SCOPUS_ID_REDIRECT: %s' % scopus_id)
        # else:
        #     NUM_PUBS += num_pubs
        #     CITES += cites

        df.loc[index, 'Documents'] = NUM_PUBS
        df.loc[index, 'Cited By'] = CITES
        df.loc[index, 'Citations'] = CITES_SELF
        df.loc[index, 'h-index'] = HINDEX

driver.close()
driver.quit()

# output
out_file = 'out.xlsx'
writer = pd.ExcelWriter(out_file)
df.to_excel(writer, sheet_name='out')
writer.close()