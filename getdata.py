# **********************************************************
# *
# *  PlutoPon
# *  fb.com/plganimation
# *
# **********************************************************
import concurrent.futures
import os
import random
import time
import argparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.chrome.service import Service as ChromeService

from serpapi import GoogleSearch

from pymongo import MongoClient
import pandas as pd

_pathfile = os.path.dirname(__file__)+"/temp"
_serpkey = ''

print(_pathfile)
# if os.name == 'nt':
#     service = Service('C:/webdrivers/chromedriver.exe')
# else:
#     service = Service('./chromedriver_mac.app')


def log(s, t=None):
    named_tuple = time.localtime()  # get struct_time
    time_string = time.strftime("%H:%M:%S", named_tuple)
    if t is not None:
        print(time_string + " " + s + f' [{int((_pd/15)*100)}%]')
    else:
        print(time_string + " " + s)


def inc_pd():
    global _pd
    _pd += 1


def reset_pd():
    global _pd
    _pd = 0


_pd = 0


dbname = {}
def defineDB(db):
    global dbname
    dbname = db

def start_driver():
    chrome_options = webdriver.ChromeOptions();
    prefs = {"download.default_directory": _pathfile}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_experimental_option("excludeSwitches", ['enable-automation','enable-logging']);
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-dev-shm-usage')
    # chrome_options.add_argument('--app=data:')
    # chrome_options.add_argument('--headless')
    return webdriver.Chrome(options=chrome_options, service=ChromeService())

driver = start_driver()

def wait(by, elem):
    result = EC.presence_of_element_located((by, elem))
    WebDriverWait(driver, 6).until(result)

def stop_driver():
    driver.quit()

def start():
    driver.set_window_position(0,2000)
    driver.maximize_window()


def refresh():
    driver.refresh()

def run_username_overall(s):
    # pre-step 1 - get data from Google Scholar with "serpAPI"
    # params = {
    #     "engine": "google_scholar_author",
    #     "author_id": "8WMbN4AAAAAJ",
    #     "api_key": _serpkey
    # }
    #
    # search = GoogleSearch(params)
    # results = search.get_dict()
    # author = results["author"]
    #
    # print(author)

    # step 1 - find auther with their name
    if 'scopus' in s and 'profile' in s['scopus']:
        driver.get(s['scopus']['profile'])
    else:
        driver.get('https://www.scopus.com/freelookup/form/author.uri?zone=TopNavBar&origin=NO%20ORIGIN%20DEFINED')
        driver.find_element(By.NAME, "searchterm1").send_keys(s['lastname'])
        driver.find_element(By.NAME, "searchterm2").send_keys(s['firstname'])
        time.sleep(1);
        wait(By.ID, 'authorSubmitBtn')
        driver.find_element(By.ID, "authorSubmitBtn").click()

        # step 2 - check if they have data in scopus then get inside dashboard page
        wait(By.ID, 'srchResultsList')
        link_dashboard = driver.find_element(By.CLASS_NAME, 'authorResultsNamesCol') \
            .find_element(By.TAG_NAME, "a") \
            .get_attribute("href")

        # update dashboard link
        authors_coll = dbname['authors']
        authors_coll.update_one({'firstname': s['firstname'], 'lastname': s['lastname']},
                                {'$set': {'scopus': {'profile':link_dashboard}}})
        driver.get(link_dashboard)
        inc_pd()
        log('Update Author Detail Successfully', True)
        prog_step3(s)
        return
    inc_pd()
    log('Bypassed query auther', True)
    prog_step3(s)

def prog_step3(s):
    # step 3 - go dashboard and get overall data
    # time.sleep(1)

    try:
        wait(By.ID, 'AuthorHeader__showAllAuthorInfo')
        driver.find_element(By.ID, 'AuthorHeader__showAllAuthorInfo').click()
    except:
        log('Forget open VPN? exit...')
        exit()
    inc_pd()
    log('Get Author Main Data', True)
    sai = driver.find_elements(By.XPATH, "//tr[contains(@class, 'AuthorInfoFlyout')]")[0].find_elements(By.TAG_NAME, 'td')[1].text
    try:
        orcid = driver.find_elements(By.XPATH, "//tr[contains(@class, 'AuthorInfoFlyout')]")[1].find_elements(By.TAG_NAME, 'td')[1].text.split('/')[-1]
    except Exception:
        orcid = None
    other_names = []

    try:
        log(driver.find_element(By.XPATH, "//h2[.='Other names']/following::span[1]").text)
        on = driver.find_element(By.XPATH, "//h2[.='Other names']/following::span[1]").text
        for name in on.split(' • '):
            other_names.insert(0, name)
    except Exception:
        other_names = []

    time.sleep(1)
    wait(By.XPATH, "//button[@data-test-id='flyout-close-button']")
    driver.find_element(By.XPATH, "//button[@data-test-id='flyout-close-button']").click()

    mectric_section = "//section[contains(@class, 'MetricSection')]//div[@data-testid='count-label-and-value']"
    citation_count = driver.find_elements(By.XPATH, mectric_section+"//span[@data-testid='unclickable-count']")[0].text
    cite_by_count = driver.find_element(By.XPATH, mectric_section).find_element(By.TAG_NAME, 'strong').text

    co_authors = driver.find_elements(By.XPATH, mectric_section+"//span[@data-testid='unclickable-count']")[1].text
    h_index = driver.find_elements(By.XPATH, mectric_section+"//span[@data-testid='unclickable-count']")[2].text


    authers_coll = dbname['authors']
    authers_coll.update_one({'firstname': s['firstname'], 'lastname': s['lastname']},{'$set': {'orcid': orcid, 'other_names': other_names, 'scopus':{'id':sai, 'profile':s['scopus']['profile'],'citation_count':citation_count,'cite_by_count':cite_by_count,'co_authors':co_authors,'h_index':h_index}}})
    s['orcid'] = orcid
    s['scopus']['id'] = sai
    s['scopus']['citation_count'] = citation_count
    s['scopus']['cite_by_count'] = cite_by_count
    s['scopus']['co_authors'] = co_authors
    s['scopus']['h_index'] = h_index
    inc_pd()
    log('Update Author detail successfully', True)
    time.sleep(.5)
    prog_step4(s, 'doc')


def prog_step4(s, type):
    inc_pd()
    log('Update ' + type + '\'s progress', True)

    if type == 'cite':
        driver.get(f'{s["scopus"]["profile"]}#tab=cited-by')
    elif type == 'co-authors':
        driver.get(f'https://www.scopus.com/results/coAuthorResults.uri?sort=count-f&src=al&authorId={s["scopus"]["id"]}&sot=al&sdt=coaut&groupIds=&authorListId=&authorListName=&origin=AuthorProfile&jtp=true&selectionPageSearch=asp&zone=coAuthorsTab')

        result = EC.presence_of_element_located((By.ID, 'srchResultsList'))
        WebDriverWait(driver, 6).until(result)

        if len(driver.find_elements(By.ID, 'resultDataRow20')) > 0 and len(driver.find_element(By.CLASS_NAME, 'pagination').find_elements(By.TAG_NAME, 'li')) > 1:
            log('Has result more than 20... just expand it.')
            result = EC.presence_of_element_located((By.ID, 'resultsPerPage-button'))
            WebDriverWait(driver, 6).until(result)
            driver.find_element(By.ID, 'resultsPerPage-button').click()
            driver.find_element(By.ID, 'ui-id-16').click()

        co_authors_coll = dbname['co_authors']
        inc_pd()
        log('Reset co-authors data')
        co_authors_coll.delete_many({'from_author': s["scopus"]["id"]})

        data = []
        wait(By.XPATH, '//tr[contains(@id, "resultDataRow")]')
        result_row = driver.find_elements(By.XPATH, '//tr[contains(@id, "resultDataRow")]')
        total = len(result_row);
        log(f'Insert new co-authors data [total: {total}]')
        i = 0

        for res in result_row:
            i+=1
            d = {
                'Author':'',
                'Author Link':'',
                'OtherName':[],
                'Documents':'',
                'Documents Link':'',
                'h-index':'',
                'Affiliation':'',
                'Affiliation Link':'',
                'City':'',
                'Country/Territory':'',
                'from_author': s['scopus']['profile']
            }
            if len(res.find_element(By.CLASS_NAME, 'authorResultsNamesCol').find_elements(By.CLASS_NAME, 'docTitle')) > 0:
                # log(res.find_element(By.CLASS_NAME, 'docTitle').text)
                d['Author'] = res.find_element(By.CLASS_NAME, 'docTitle').text
                d['Author Link'] = res.find_element(By.CLASS_NAME, 'docTitle').get_attribute('href')
            else:
                # log(res.find_element(By.CLASS_NAME, 'authorResultsNamesCol').text)
                d['Author'] = res.find_element(By.CLASS_NAME, 'authorResultsNamesCol').text

            if len(res.find_element(By.CLASS_NAME, 'authorResultsNamesCol').find_elements(By.CLASS_NAME, 'txtSmaller')) > 0:
                # driver.execute("$('.displayNone').removeClass('displayNone')")
                for names in res.find_element(By.CLASS_NAME, 'authorResultsNamesCol').find_elements(By.CLASS_NAME, 'txtSmaller'):
                    if names.text.strip() != '':
                        # log(names.text)
                        d['OtherName'].insert(0, names.text)

            d['Documents'] = res.find_element(By.XPATH, "//td[contains(@id,'resultsDocumentsCol')]").find_element(By.TAG_NAME, 'a').text
            d['Documents Link'] = res.find_element(By.XPATH, "//td[contains(@id,'resultsDocumentsCol')]").find_element(By.TAG_NAME, 'a').get_attribute('href')

            d['h-index'] = res.find_element(By.CLASS_NAME, 'dataCol4').text

            d['Affiliation'] = res.find_element(By.CLASS_NAME, 'dataCol5').find_element(By.TAG_NAME, 'a').find_element(By.TAG_NAME, 'span').text
            d['Affiliation Link'] = res.find_element(By.CLASS_NAME, 'dataCol5').find_element(By.TAG_NAME, 'a').get_attribute('href')

            d['City'] = res.find_element(By.CLASS_NAME, 'dataCol6').text
            d['Country/Territory'] = res.find_element(By.CLASS_NAME, 'dataCol7').text
            data.append(d)
            log(f'Inserted new co-authors data [{i}/{total}]')

        co_authors_coll.insert_many(data)
        inc_pd()
        log('Co-authors update complete!', True)
        # prog_step4(s, 'topics') # skip topics
        prog_step4(s, 'getinfo')

        return
    elif type == 'topics':
        driver.get(f'{s["scopus"]["profile"]}#tab=topics')

        result = EC.presence_of_element_located((By.XPATH, '//table[contains(@id, "TopicsTable")]'))
        WebDriverWait(driver, 15).until(result)

        topic_col = dbname['topics']
        inc_pd()
        log('Reset topics data')
        topic_col.delete_many({'from_author': s['scopus']['id']})

        data = []
        if len(driver.find_element(By.XPATH, '//table[contains(@id, "TopicsTable")]').find_element(By.TAG_NAME, 'tbody').find_elements(By.TAG_NAME, 'tr')) > 0:
            inc_pd()
            total = len(driver.find_element(By.XPATH, '//table[contains(@id, "TopicsTable")]').find_element(By.TAG_NAME, 'tbody').find_elements(By.TAG_NAME, 'tr'))
            log(f'Insert new topics data [total: {total}]')
            i = 0
            for tb in driver.find_element(By.XPATH, '//table[contains(@id, "TopicsTable")]').find_element(By.TAG_NAME, 'tbody').find_elements(By.TAG_NAME, 'tr'):
                i+=1
                log(f'Insert new topics data [{i}/{total}]')
                d = {
                    'Topic':tb.find_element(By.CLASS_NAME, 'scopus-author-topics--topics-table--topic-name').find_element(By.TAG_NAME, 'button').text,
                    'TWFC impact':tb.find_element(By.CLASS_NAME, 'scopus-author-topics--topics-table--fwci').text,
                    'Author documents': [],
                    'from_author': s['scopus']['id']
                }

                tb.find_element(By.ID, 'scopus-author-profile-page-control-microui__scopus-author-topics__topics-table--author-documents-button').click()

                result = EC.presence_of_element_located((By.XPATH, '//ul[contains(@class, "AuthorDocuments")]//li[contains(@class,"DocumentsListItem")]'))
                WebDriverWait(driver, 60).until(result)
                if len(driver.find_element(By.XPATH, '//ul[contains(@class, "AuthorDocuments")]//li[contains(@class,"DocumentsListItem")]').find_elements(By.TAG_NAME, 'li')) > 0:
                    ad = {}
                    log(f'Get author documents topic {d["Topic"]}')
                    for fld in driver.find_elements(By.XPATH, '//ul[contains(@class, "AuthorDocuments")]//li[contains(@class, "DocumentsListItem")]'):
                        ad['eid'] = fld.find_element(By.CLASS_NAME, 'col-18').find_element(By.TAG_NAME, 'h5').find_element(By.TAG_NAME, 'a').get_attribute('href').split("eid=")[1].split("&")[0]
                        ad['fwci'] = float(fld.find_elements(By.CLASS_NAME, 'col-3')[1].find_element(By.CLASS_NAME,'text-meta--large').text)
                        # ad['fwci'] = float(fld.find_elements(By.XPATH, '//div[@class="col-3"]//span[@class="text-meta--large"]')[1].text)
                        d['Author documents'].append(ad)

                data.append(d)
                driver.find_element(By.XPATH, '//els-modal[@id="scopus-author-topics--topic-modal"]//header//button').click()
        #         id="scopus-author-topics--topic-modal"
        #         button__icon icon--no-border

        topic_col.insert_many(data)
        inc_pd()
        log('Topics update complete!', True)
        prog_step4(s, 'getinfo')
        return
    elif type == 'getinfo':
        doct_col = dbname['documents']
        cite_col = dbname['citations']

        inc_pd()
        total = 0
        dc = doct_col.find({'Author(s) ID': {'$regex': s["scopus"]["id"]}})
        for d in dc:
            if d['Cited by'] > 0:
                total += 1
        dc = doct_col.find({'Author(s) ID': {'$regex': s["scopus"]["id"]}})
        log(f'Getting FWCI & defined citation information [documents total: {total}]')
        i = 0
        for doc in dc:
            if doc['Cited by'] > 0:
                i+=1
                # //Getting FWCI
                # log(f'Getting FWCI & defined citation information [{i}/{total}]')
                # driver.get(f'https://www.scopus.com/record/display.uri?eid={doc["EID"]}&origin=resultslist')
                # result = EC.presence_of_element_located((By.XPATH, '//els-info-field[@class="sc-els-info-field-h sc-els-info-field-s hydrated"]'))
                # WebDriverWait(driver, 10).until(result)
                # time.sleep(1)
                # fwci = float(driver.find_elements(By.XPATH, '//els-info-field[@class="sc-els-info-field-h sc-els-info-field-s hydrated"]')[1].get_attribute('value'))

                time.sleep(1)
                log(f'Getting defined citation information [{i}/{total}]')
                cited = []
                driver.get(f'https://www.scopus.com/results/citedbyresults.uri?cite={doc["EID"]}&src=s&sot=cite&sdt=a&origin=resultslist')

                result = EC.presence_of_element_located((By.ID, 'srchResultsList'))
                WebDriverWait(driver, 6).until(result)

                if len(driver.find_elements(By.ID, 'resultDataRow20')) > 0 and len(
                        driver.find_element(By.CLASS_NAME, 'pagination').find_elements(By.TAG_NAME, 'li')) > 1:
                    result = EC.presence_of_element_located((By.ID, 'resultsPerPage-button'))
                    WebDriverWait(driver, 6).until(result)
                    driver.find_element(By.ID, 'resultsPerPage-button').click()
                    driver.find_element(By.ID, 'ui-id-16').click()

                for rd in driver.find_elements(By.XPATH, '//tr[contains(@id, "resultDataRow")]'):
                    if len(rd.find_element(By.XPATH, '//td[@data-type="docTitle"]').find_elements(By.TAG_NAME, 'a')) > 0:
                        cited.append(rd.find_element(By.CLASS_NAME, 'ddmDocTitle').get_attribute('href').split("eid=")[1].split("&")[0])
                # doct_col.update_one({'EID': doc["EID"]}, {'$set': {'FWCI': fwci, 'Cited documents': cited}})
                # cite_col.update_one({'EID': doc["EID"]}, {'$set': {'FWCI': fwci, 'Cited documents': cited}})
                doct_col.update_one({'EID': doc["EID"]}, {'$set': {'Cited documents': cited}})
                cite_col.update_one({'EID': doc["EID"]}, {'$set': {'Cited documents': cited}})
        inc_pd()
        log('Information update complete!', True)
        return

    if len(driver.find_elements(By.XPATH, '//div[contains(@class, "empty-results")]')) > 0:
        raise TimeoutException('EmptyResults')
    time.sleep(1)
    try:
        try:
            result = EC.presence_of_element_located((By.ID, 'export_results'))
            WebDriverWait(driver, 6).until(result)
            driver.find_element(By.ID, 'export_results').click()
        except Exception:
            driver.refresh()
            time.sleep(1)
            result = EC.presence_of_element_located((By.ID, 'export_results'))
            WebDriverWait(driver, 6).until(result)
            driver.find_element(By.ID, 'export_results').click()
        time.sleep(2)
        result = EC.presence_of_element_located((By.ID, 'exportList'))
        WebDriverWait(driver, 6).until(result)
        while 1:
            try:
                driver.find_element(By.ID, 'exportList').find_elements(By.TAG_NAME, 'li')[3].click()
                break
            except:
                wait(By.ID, 'export_results')

                driver.get(s['scopus']['profile'])
                wait(By.ID, 'export_results')
                driver.find_element(By.ID, 'export_results').click()
        time.sleep(1)
        wait(By.ID, 'exportTrigger')
        driver.find_element(By.ID, 'exportTrigger').click()

        # step 4 - wait downloaded documents detail file and kept it to database
        found_file = False
        while found_file is False:
            if len(driver.find_elements(By.CLASS_NAME, 'errText')) > 0:
                rd = random.randint(1, 15)
                log(f'had error during progress. Restarting progress in {rd} seconds...')
                time.sleep(rd)
                reset_pd()
                run_username_overall(s)
                return

            for filename in os.listdir(_pathfile):
                if filename == 'scopus.csv':
                    found_file = True
                    inc_pd()
                    log('File downloaded complete!')
                    prog_step4_1(s, type)
                    break
            time.sleep(2)
    except (TimeoutException, StaleElementReferenceException) as ex:
        inc_pd()
        inc_pd()
        log('Dont have '+type+' documents, skip...')
        prog_step4(s, 'co-authors')
    except Exception as e:
        print("deb->"+repr(e))
        if driver.current_url == "https://www.scopus.com/error.uri":
            rd = random.randint(1, 15)
            log(f'had error during progress. Restarting progress in {rd} seconds...')
            time.sleep(rd)
            reset_pd()
            run_username_overall(s)
            return

def prog_step4_1(s,type):
    df = pd.read_csv('temp/scopus.csv')

    if type == 'doc':
        documents_coll = dbname['documents']

        # reset document of author and replace with new data
        log('Reset this author\'s documents')
        documents_coll.delete_many({'Author(s) ID': {'$regex': s['scopus']['id']}})
        td = df.to_dict('records')
        documents_coll.insert_many(td)

        s['scopus']['publications'] = len(td)
        authers_coll = dbname['authors']
        authers_coll.update_one({'firstname': s['firstname'], 'lastname': s['lastname']}, {'$set': {'scopus': s['scopus']}})

        inc_pd()
        log('update complete!', True)
        os.remove(_pathfile+'/scopus.csv')

        prog_step4(s, 'cite')
    elif type == 'cite':
        documents_coll = dbname['citations']
        # reset document of author and replace with new data
        log('Reset this author\'s cited documents')
        documents_coll.delete_many({'from_author': s['scopus']['id']})
        cite = df.to_dict('records')
        for data in cite:
            data['from_author'] = s['scopus']['id']
        documents_coll.insert_many(cite)

        inc_pd()
        log('Update complete!', True)
        os.remove(_pathfile+'/scopus.csv')

        prog_step4(s, 'co-authors')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-fn", "--firstname", required=True, help="FirstName of the author")
    parser.add_argument("-ln", "--lastname", required=True, help="LastName of the author")
    args = parser.parse_args()

    log('Finding author ' +args.firstname+ ' '+ args.lastname+'...')

    authers_coll = dbname['authors']
    s = authers_coll.find_one({'firstname': args.firstname, 'lastname': args.lastname})

    for filename in os.listdir(_pathfile):
        if filename == 'scopus.csv':
            os.remove(_pathfile+'/'+filename)

    start()

    log('Process Starting...')
    time.sleep(1)

    run_username_overall(s)


def runner(fn, ln, sk):
    global _serpkey
    _serpkey = sk
    log('Finding author ' + fn + ' ' + ln + '...')

    authers_coll = dbname['authors']
    s = authers_coll.find_one({'firstname': fn, 'lastname': ln})

    for filename in os.listdir(_pathfile):
        if filename == 'scopus.csv':
            os.remove(_pathfile + '/' + filename)

    start()

    log('Process Starting...')
    # time.sleep(1)

    run_username_overall(s)
    # "errText" is class when Document Error

    stop_driver()
