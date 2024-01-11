import os
from tqdm import tqdm
import pandas as pd
import mariadb
import mariadb.connections

try:
    conn = mariadb.connect(
        user="itrms",
        password="it2024rms",
        host="127.0.0.1",
        port=3306,
        database="itrms"
    )
    conn.auto_reconnect = True
    print(f"Connected to MariaDB Platform successfully.")
except mariadb.Error as e:
    print(f"Error connecting to MariaDB Platform: {e}")

cursor = conn.cursor()

_pathfile = os.path.dirname(__file__)+"/temp copy"

# [EDIT] dataframe from input xlsx
df = pd.read_excel('sample.xlsx', dtype=str)

def __setup_insert_master_data(df):
    for index, row in tqdm(df.iterrows(), total=len(df), desc="Authors Processing"):
        row = row.copy()

        scopus_ids = str(row['Scopus ID']).split('; ')
        links = ['https://www.scopus.com/authid/detail.url?authorId=%s' %
                scopus_id for scopus_id in scopus_ids]

        # Sample data to insert
        data_to_insert = (row['NameEn'].strip(), row['NameTh'].strip(), "IT")

        # SQL query to insert data into a table
        insert_query = "INSERT INTO master_detail (name_en, name_th, faculty) VALUES (%s, %s, %s)"

        # Execute the query with the data
        cursor.execute(insert_query, data_to_insert)

        first_table_id = cursor.lastrowid

        print(f'insert {data_to_insert} ({first_table_id})')

        for i in range(0, len(scopus_ids)):
            if scopus_ids[i] == "nan":
                data_to_insert = (first_table_id, None, None)
            else:
                data_to_insert = (first_table_id, scopus_ids[i], links[i])

            print(scopus_ids[i])

            # SQL query to insert data into a table
            insert_query = "INSERT INTO master_scopus (mid, sid, link) VALUES (%s, %s, %s)"

            cursor.execute(insert_query, data_to_insert)

        conn.commit()

def __setup_update_scopus_docs(df):
    for index, row in tqdm(df.iterrows(), total=len(df), desc="Authors Processing"):
        row = row.copy()

        scopus_ids = str(row['Scopus ID']).split('; ')
        for i in range(0, len(scopus_ids)):
            if scopus_ids[i] == "nan":
                continue

            docs_file = f'{_pathfile}/docs_{index}{"-"+i if i != 0 else ""}.csv'
            cited_file = f'{_pathfile}/cited_{index}{"-"+i if i != 0 else ""}.csv'

            if os.path.isfile(docs_file):
                df = pd.read_csv(docs_file)
                df = df.fillna('')
                docs_amount = len(df)
                readCSVToDB(df, scopus_ids[i], "doc")
            if os.path.isfile(cited_file):
                df = pd.read_csv(cited_file)
                df = df.fillna('')
                citedby_amount = len(df)
                readCSVToDB(df, scopus_ids[i], "cite")

            updateStatsToDB(scopus_ids[i], docs_amount, citedby_amount, 0, 0)

def getDocumentsFromDb(sid, year_in, year_end):
    query ="CALL getDocumentsBySid(%s, %s, %s)"

    data_to_q = (sid, year_in, year_end)
    cursor.execute(query, data_to_q)

    # Fetch the column headers
    columns = [column[0] for column in cursor.description]

    # Fetch the results
    result_set = cursor.fetchall()
    # Convert each row to a dictionary
    result_list = []
    for row in result_set:
        result_dict = dict(zip(columns, row))
        result_list.append(result_dict)

    return result_list

def getSummaryCountFromDb(sid, year_in, year_end):
    result_list = getDocumentsFromDb(sid, year_in, year_end)
    # Store the results with dictionary-like access
    data = [ ]

    for result_dict in result_list:
        # print(result_dict['title'], result_dict['year'], result_dict['cited_by'])
        result_d = {"name": result_dict['title'], "year": result_dict['year'], "citation": int(result_dict['cited_by'])}
        data.append(result_d)

    print(data)

def getHindexFromDb(sid, year_in, year_end):
    result_list = getDocumentsFromDb(sid, year_in, year_end)
    # Store the results with dictionary-like access
    data = [
    ]
    for result_dict in result_list:
        # print(result_dict['title'], result_dict['year'], result_dict['cited_by'])
        result_d = {"name": result_dict['title'], "year": result_dict['year'], "citation": int(result_dict['cited_by'])}
        data.append(result_d)

    hindex = calculateHindex(data)
    # print(f'H-index: {hindex}')
    return hindex

def updateStatsToDB(sid, docs_amount, citedby_amount, cited_amount, hindex):
    query = "UPDATE master_scopus SET docs_amount = %(docs_amount)s, citedby_amount = %(citedby_amount)s, cited_amount = %(cited_amount)s, hindex = %(hindex)s WHERE sid = %(sid)s"
    data_to_q = {
        'docs_amount': docs_amount,
        'citedby_amount': citedby_amount,
        'cited_amount': cited_amount,
        'hindex': hindex,
        'sid': sid
    }
    cursor.execute(query, data_to_q)
    conn.commit()

def readCSVToDB(file, aid, type):
    cursor = conn.cursor()
    for index, row in file.iterrows():
        # print(len(row["References"]))
        query = """
            INSERT INTO `scopus_documents` 
            (`doi`, `eid`, `authors`, `author_full_names`, `authors_id`, `title`, `year`, `source_title`, `volume`, 
            `issue`, `art_no`, `page_start`, `page_end`, `page_count`, `cited_by`, `link`, `references`, 
            `publication_state`, `for_aid`, `for_type`) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            `doi` = VALUES(`doi`), 
            `authors` = VALUES(`authors`), 
            `author_full_names` = VALUES(`author_full_names`), 
            `authors_id` = VALUES(`authors_id`), 
            `title` = VALUES(`title`), 
            `year` = VALUES(`year`), 
            `source_title` = VALUES(`source_title`), 
            `volume` = VALUES(`volume`), 
            `issue` = VALUES(`issue`), 
            `art_no` = VALUES(`art_no`), 
            `page_start` = VALUES(`page_start`), 
            `page_end` = VALUES(`page_end`), 
            `page_count` = VALUES(`page_count`), 
            `cited_by` = VALUES(`cited_by`), 
            `link` = VALUES(`link`), 
            `references` = VALUES(`references`), 
            `publication_state` = VALUES(`publication_state`)
        """
        values = (
            row['DOI'], row['EID'], row['Authors'], row['Author full names'], row['Author(s) ID'],
            row['Title'], row['Year'], row['Source title'], row['Volume'],
            row['Issue'], row['Art. No.'], row['Page start'], row['Page end'],
            row['Page count'], row['Cited by'], row['Link'], row['References'],
            row['Publication Stage'], aid, type
        )

        cursor.execute(query, values)
        conn.commit()

#* H-index Calculated process by ChatGPT - Ponlawat
#* Based of Concept: https://philoflanguage.wordpress.com/2020/06/26/h-index-%E0%B8%84%E0%B8%B7%E0%B8%AD%E0%B8%AD%E0%B8%B0%E0%B9%84%E0%B8%A3-%E0%B9%83%E0%B8%8A%E0%B9%89%E0%B8%97%E0%B8%B3%E0%B8%AD%E0%B8%B0%E0%B9%84%E0%B8%A3/
def calculateHindex(publications):
    publications.sort(key=lambda x: x['citation'], reverse=True)
    h_index = 0

    for i, publication in enumerate(publications, start=1):
        if i <= publication['citation']:
            h_index = i
        else:
            break

    return h_index

# __setup_update_scopus_docs(df)
# hindex = getHindexFromDb('25031719700', 1000, 2024)
# getSummaryCountFromDb('16176331500', 1000, 2024)
# print(f'H-index: {hindex}')