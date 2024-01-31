#!/usr/bin/env python3

import RPi.GPIO as GPIO
import time
from datetime import datetime
import sys, os, socket, subprocess, re
import math
from luma.core.interface.serial import i2c
from luma.core.render import canvas as canvas2
from luma.oled.device import ssd1306
from PIL import ImageFont

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import print_fact_by_category
from src.db_utils import init_db

# Set GPIO mode (BCM or BOARD)
GPIO.setmode(GPIO.BOARD)

# Define GPIO pin for the button
button_select_pin = 11  # BCM 17 on rpi 4
button_up_pin = 15  # BCM 27 on rpi 4
button_down_pin = 13  # BCM 22 on rpi 4

# Setup the button pin as input with pull-up resistor
GPIO.setup(button_select_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(button_up_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(button_down_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

### setting up OLED screen
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial, mode="1", width=128, height=32)

#PWD = os.getcwd()
PWD = "/opt/fun-facts"
CATEGORIES = []
INFO_TEXT = "==_I_N_F_O_=="
SELECTED_POSITION = 0
printing = False
printing_error = False
show_machine_status = False

# Set the font size
font_size = 15
font = ImageFont.truetype(PWD + '/src/fonts/Ubuntu-Regular.ttf', font_size)
font_bold = ImageFont.truetype(PWD + "/src/fonts/Ubuntu-Bold.ttf", font_size)
font_small = ImageFont.truetype(PWD + '/src/fonts/Ubuntu-Regular.ttf', 9)

# clock_font_size = 18
# clock_font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" 
# clock_font_bold = ImageFont.truetype(clock_font_path, font_size)

print("Staring fun-fact demon...")

def get_categories():
    global CATEGORIES
    conn, cursor = init_db()
    sql = """SELECT DISTINCT(category) from facts ORDER BY category"""
    categories = ["random_fact"]

    cursor.execute(sql)
    for row in cursor:
        categories.append(row[0])

    categories.append(INFO_TEXT)

    if conn:
        conn.commit()
        conn.close()

    CATEGORIES = categories

get_categories()


def get_total_prints():
    conn, cursor = init_db()
    sql = """SELECT SUM(times_used) as total_sum from facts"""
    total = 0

    cursor.execute(sql)
    row = cursor.fetchone()
    total = row[0]

    if conn:
        conn.commit()
        conn.close()

    return str(total)

# def screen_saver():
#     fun_fact_started = False
#     try:
#         dots_visible = True
#         while True and not fun_fact_started:
#             current_time = datetime.now().strftime("%H:%M:%S") if dots_visible else datetime.now().strftime("%H %M %S")

#             with canvas2(device) as draw:
#                 draw.text((5, 10), current_time, fill="white", font=clock_font_bold)
#             dots_visible = not dots_visible
#             time.sleep(1)

#     except KeyboardInterrupt:
#         device.clear()

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip =  s.getsockname()[0]
        s.close()
        return ip
    except socket.error as e:
        print(f"Error getting local IP: {e}")
    return "NOT CONNECTED!"

def get_uptime():
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])
    return str(math.ceil(uptime_seconds / 60)) + "min"

def draw_menu():
    with canvas2(device) as draw:
        draw.rectangle(device.bounding_box, outline="white", fill="black")
        y = 2


        if printing:
            draw.text((5, 8), "Printing fact...", fill="white", font=font_bold)

        elif printing_error:
            draw.text((5, 8), "Error Printing :(", fill="white", font=font_bold)

        elif show_machine_status:
            my_ip =  get_local_ip()
            draw.text((5, 1), f"My  IP: {my_ip}", fill="white", font=font_small)
            draw.text((5, 10), "Uptime: " + get_uptime(), fill="white", font=font_small)
            draw.text((5, 20), "Total prints: " + get_total_prints(), fill="white", font=font_small)

        else:
            for idx, item in enumerate(CATEGORIES):
                if idx >= SELECTED_POSITION:
                    if idx == SELECTED_POSITION:
                        draw.text((5, y), "* " + " ".join(str(item).split("_")).title(), fill="white")
                    else:
                        draw.text((10, y), "  " + " ".join(str(item).split("_")).title(), fill="white")

                    y += 10

def button_up_callback(channel):
    print("Button UP Pressed!")
    global SELECTED_POSITION

    if GPIO.input(channel) == GPIO.LOW:
        if SELECTED_POSITION == 0:
            SELECTED_POSITION = len(CATEGORIES) -1
        else:
            SELECTED_POSITION -= 1

def button_down_callback(channel):
    print("Button DOWN Pressed!")
    global SELECTED_POSITION
    if GPIO.input(channel) == GPIO.LOW:
        if SELECTED_POSITION == len(CATEGORIES) -1:
            SELECTED_POSITION = 0
        else:
            SELECTED_POSITION += 1

def button_accept_callback(channel):
    print("Button ACCEPT Pressed!")
    global SELECTED_POSITION, printing, printing_error, show_machine_status
    category = CATEGORIES[SELECTED_POSITION]
    print("category", category)
    success = False
    if GPIO.input(channel) == GPIO.LOW:
        printing = True
        if category == "random_fact":
            success = print_fact_by_category()
        elif category == INFO_TEXT:
            printing = False
            show_machine_status = True
        else:
            success = print_fact_by_category(category)

        if success:
            time.sleep(1)
            printing = False
        elif show_machine_status:
            time.sleep(4)
            show_machine_status = False
        else:
            time.sleep(1)
            printing = False
            printing_error = True
            time.sleep(3)
            printing_error = False

        # SELECTED_POSITION = 0

GPIO.add_event_detect(button_up_pin, GPIO.BOTH, callback=button_up_callback, bouncetime=300)
GPIO.add_event_detect(button_down_pin, GPIO.BOTH, callback=button_down_callback, bouncetime=300)
GPIO.add_event_detect(button_select_pin, GPIO.BOTH, callback=button_accept_callback, bouncetime=300)

try:
    while True:
        draw_menu()
        time.sleep(0.05)

except KeyboardInterrupt:
    pass

finally:
    print("Exiting...")
    device.clear()
    GPIO.cleanup()
