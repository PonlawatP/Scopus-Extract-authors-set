import os
from selenium import webdriver
from time import sleep
from tqdm import tqdm
import pandas as pd
import requests
import json
import datetime

import db_insert_master as db

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

api_headers = {
    "Accept": "application/json",
    "X-ELS-APIKey": "05bf281f96c4275d3c1f45a07b0cf5f1"
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
    chrome_options.add_argument('--disable-features=DownloadBubble') 
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
    'export_download_1': '//input[@id="field_group_sourceDocumentType"]',
    'export_download_2': '//input[@id="field_group_openAccess"]',
    'export_download_3': '//input[@id="field_group_references"]',
    'export_download_4': '//input[@data-testid="truncate-information-switch"]',
    'export_close_modal': '//*[@data-testid="modal-dismiss"]',
}
    # 'export_download_2': '//input[@id="field_group_doi"]',

def waitForElement(elem):
    result = EC.presence_of_element_located(elem)
    WebDriverWait(driver, 10).until(result)
# download fild and wait until complete
def downloadFileProcess(title="file", index=0, subindex=0, proc_1=(), proc_2=(), proc_3=()):
    try:
        proc_1()

        # wait downloaded documents detail file and kept it to database
        clicked = False
        while clicked is False:
                sleep(1)
                # try:
                
                for download_index in range(1, 5):
                    waitForElement((By.XPATH, elems[f'export_download_{download_index}']))
                    driver.find_element(By.XPATH, elems[f'export_download_{download_index}']).click()
                sleep(0.5)

                while clicked is False:
                    sleep(0.5)
                    proc_2()
                    print("click")

                    try:
                        driver.find_element(By.XPATH, elems['export_close_modal'])
                        continue
                    except NoSuchElementException:
                        clicked = True
                # except:
                #     break

        found_file = False
        while clicked is True and found_file is False:
            sleep(.5)
            if os.path.isfile(f'{_pathfile}/scopus.csv'):
                old_name = f'{_pathfile}/scopus.csv'
                new_name = f'{_pathfile}/{title}_{index}{"-"+subindex if subindex != 0 else ""}.csv'
                os.rename(old_name, new_name)
                found_file = True
                proc_3()
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

        driver.execute_script('window.scrollBy(0,300)')

        docs_file = f'{_pathfile}/docs_{index}{"-"+i if i != 0 else ""}.csv'
        cited_file = f'{_pathfile}/cited_{index}{"-"+i if i != 0 else ""}.csv'

        # 02 load documents
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
                                    driver.find_element(By.XPATH, elems['export_document_3']).click(),
                                )
                            ),
                            proc_3=(
                                lambda: (
                                    db.readCSVToDB(pd.read_csv(docs_file).fillna(''), scopus_id, "doc")
                                )
                            ),
        )

        # 03 load citedby
        downloadFileProcess(title='cited', 
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
                                    driver.find_element(By.XPATH, elems['export_cited_4']).click()
                                )
                            ),
                            proc_3=(
                                lambda: (
                                    db.readCSVToDB(pd.read_csv(cited_file).fillna(''), scopus_id, "cite")
                                )
                            ),
        )

        # throw a warning if the scopus link get redirect somewhere else
        if scopus_id != info:
            print('[WARN] SCOPUS_ID_REDIRECT: %s' % scopus_id)
        # else:
        #     NUM_PUBS += num_pubs
        #     CITES += cites

        hindex = db.getHindexFromDb(scopus_id, 0, datetime.date.today().year)
        db.updateStatsToDB(scopus_id, NUM_PUBS, CITES, CITES_SELF, hindex)

driver.close()
driver.quit()

# for index, row in tqdm(df.iterrows(), total=len(df), desc="Authors Processing"):
#     row = row.copy()

#     scopus_ids = str(row['Scopus ID']).split('; ')

#     for i in range(0, len(scopus_ids)):
#         if scopus_ids[i] == "nan":
#             continue

#         docs_file = f'{_pathfile}/docs_{index}{"-"+i if i != 0 else ""}.csv'
#         cited_file = f'{_pathfile}/cited_{index}{"-"+i if i != 0 else ""}.csv'

#         df.loc[index, 'Documents'] = NUM_PUBS
#         df.loc[index, 'Cited By'] = CITES
#         df.loc[index, 'Citations'] = CITES_SELF

# # output
# out_file = 'out.xlsx'
# writer = pd.ExcelWriter(out_file)
# df.to_excel(writer, sheet_name='out')
# writer.close()