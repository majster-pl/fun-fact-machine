#!/usr/bin/env python3

# Copyright (c) 2024 Szymon Waliczek <szymon@waliczek.org>
# Author: Szymon Waliczek
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import cups
import random
import time
# import sys
import json
import os
import textwrap
# from reportlab.lib.pagesizes import landscape
from reportlab.pdfgen import canvas
from reportlab.lib import utils
from datetime import datetime
from src.db_utils import init_db
import logging

#PWD = os.getcwd()
PWD = "/opt/fun-facts"

script_directory = os.path.dirname(os.path.abspath(__file__))
logs_path = os.path.join(script_directory, 'fun_fact_logs.log')

# Configure the logging module
logging.basicConfig(
    filename=logs_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S',
)

PRINTER_NAME = 'BIXOLON_SRP-E300'

def fetch_and_parse_json(url=None):
    # try:
    #     # Make a GET request to the URL
    #     response = requests.get(url)

    #     # Check if the request was successful (status code 200)
    #     if response.status_code == 200:
    #         # Parse the JSON data
    #         data = json.loads(response.text)
    #         return data
    #     else:
    #         print(f"Error: Unable to fetch data. Status code: {response.status_code}")
    # except Exception as e:
    #     print(f"Error: {e}")
    file_path = PWD + "/src/facts.json"
    with open(file_path, 'r') as file:
        data = json.load(file)
        return data
    
def create_pdf(file_path, image_path, text):
    success = True
    
    try:
        width, height = 200, 200
        print("generating pdf...")
        c = canvas.Canvas(file_path, pagesize=(width, height))

        # check if given img exists...
        if not os.path.exists(image_path):
            image_path = os.path.join(script_directory, "src", "images", "about_me.png")

        # Draw the image on the PDF
        img = utils.ImageReader(image_path)
        print(img)
        c.drawImage(img, 75, height - 50, width=50, height=50)

        # Add text to the PDF with line breaks and wrapping
        text_object = c.beginText(7, height - 65)
        text_object.setFont("Helvetica", 10)

        # Split the input text by newline and add each line to the text object
        lines = text.split("\n")
        for line in lines:
            text_object.textLine(line)

        c.drawText(text_object)
        c.setFont('Helvetica', 7.5)

        # Add time and date at the bottom
        current_datetime = datetime.now()
        human_readable_date = current_datetime.strftime("%H:%M:%S %d %B %Y")
        c.drawString(7, height - 140, human_readable_date)

        # Save the PDF
        c.save()
    except:
        success = False
    finally:
        if success:
            print("pdf generated successfully")

    return success


def print_fact(pdf_file_path=None):
    conn = cups.Connection()
    printers = conn.getPrinters()
    success = False

    if not pdf_file_path:
        logging.error(f"No path to pdf provided")
        return success

    # print("printers", printers[printer_name])
    if PRINTER_NAME not in printers:
        print(f"Printer '{PRINTER_NAME}' not found.")
        return success

    # Print a file
    print_id = conn.printFile(
        PRINTER_NAME,
        pdf_file_path,
        "Print Job",
        {
            "page-ranges": "1-1",
            "document-format": "application/pdf"
        }
    )
    if print_id:
        success = True
        print(f"Print job sent to {PRINTER_NAME}. Job ID: {print_id}")

    return success


def get_random_category():
    conn, cursor = init_db()
    sql = """SELECT category FROM facts GROUP BY category ORDER BY RANDOM() LIMIT 1"""
    cursor.execute(sql)
    row = cursor.fetchone()
    random_category = row[0]

    if conn:
        conn.close()

    return random_category

def get_fun_fact(category=None):
    conn, cursor = init_db()
    current_timestamp = int(time.time())

    smallest_times_used_sql = """SELECT times_used FROM facts WHERE category = ? ORDER BY times_used ASC LIMIT 1"""

    if not category:
        category = get_random_category()

    cursor.execute(smallest_times_used_sql, (category, ))
    row = cursor.fetchone()
    smallest_times_used = row[0]

    sql = """SELECT id, times_used, category, description FROM facts 
                WHERE category = ? AND times_used = ? ORDER BY RANDOM() LIMIT 1"""

    cursor.execute(sql, (category, smallest_times_used))
    row = cursor.fetchone()
    fact_id, times_used, category, random_fact = row

    update_sql = """
                UPDATE facts
                SET times_used = ?, update_ts = ?
                WHERE id = ?;
    """
    cursor.execute(update_sql, (times_used + 1, current_timestamp, fact_id))

    # if random_fact:
    if random_fact == "stats":
        sql = """SELECT SUM(times_used) as total_sum FROM facts"""
        cursor.execute(sql)
        row = cursor.fetchone()
        total_prints = row[0]
        random_fact = f"I've printed {total_prints} facts in total and used around {total_prints * 8 / 100}m of paper."

    if conn:
        conn.commit()
        conn.close()

    return random_fact, category


def print_fact_by_category(_category=None):
    if not _category:
        logging.info(f"Generating random fact...")
    else:
        logging.info(f"Generating fun fact in category: {_category}")
    
    success = False
    # currently not used, using local file instead
    # json_url = "https://waliczek.org/downloads/facts.json"
  
    fun_fact, category = get_fun_fact(_category)

    if fun_fact == "stats":
        fun_fact = "I'"

    # split text to fit on the paper
    wrapped_content = " ".join(str(category).split("_")).title() + ':\n' + textwrap.fill(fun_fact, 40) + '\n' * 4

    print("Your random fact:", fun_fact)

    # pdf_file_path =  '/tmp/fact_to_print.pdf'
    image_path = os.path.join(script_directory, "src", "images", category+".png")
    pdf_file_path = os.path.join(script_directory, "fact_to_print.pdf")

    pdf = create_pdf(pdf_file_path, image_path, wrapped_content)

    if pdf:
        logging.info(f"Printing fact from [{category}]: {fun_fact}")
        success = print_fact(pdf_file_path)
    else:
        logging.error(f"There was an error printing fact, check printer status and if USB cable connected correctly!")
        print("Error generating pdf... exiting.")

    return success

