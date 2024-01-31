import sqlite3
import os, time
import json

script_directory = os.path.dirname(os.path.abspath(__file__))
database_path = os.path.join(script_directory, 'facts.db')
fact_json_path = os.path.join(script_directory, 'facts.json')

def fetch_and_parse_json():
    with open(fact_json_path, 'r') as file:
        data = json.load(file)
        return data

def populate_db(conn, cursor):
    json_data = fetch_and_parse_json()
    current_timestamp = int(time.time())

    for category in json_data:
        print(f"Adding {category} to database...")
        facts = json_data[category]
        for fact in facts:
            sql = """
                    INSERT INTO facts (category, description, times_used, owner, create_ts, update_ts)
                    VALUES (?,?,?,?,?,?);
            """
            cursor.execute(sql, (category, fact, 0, "szymon", current_timestamp, current_timestamp))

    if conn:
        conn.commit()
        conn.close()

def init_db():
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        description TEXT,
        times_used INTEGER,
        owner TEXT,
        create_ts DATETIME,
        update_ts DATETIME
        )
    ''')

    sql = """SELECT COUNT(id) FROM facts"""
    cursor.execute(sql)
    row = cursor.fetchone()
    entires_count = row[0]

    print("\n\nFACTS COUNT:", entires_count)

    if not entires_count:
        populate_db(conn, cursor)

    # reopen connection
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    return conn, cursor
