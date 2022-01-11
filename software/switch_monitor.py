import os
import sys
import time
import argparse
import RPi.GPIO as GPIO

from enum import Enum
from urllib.request import urlopen

ADD_DATA_PATH = "/var/lib/activity-indicator"

class con_led_state(Enum):
        OFF = 0
        RED = 1
        GREEN = 2

def check_connection():
        try:
                urlopen('http://www.google.com', timeout=1)
                return True
        except:
                return False

def set_con_led(red_pin: int, green_pin: int, state: con_led_state):
        if state == con_led_state.OFF:
                GPIO.output(red_pin, GPIO.LOW)
                GPIO.output(green_pin, GPIO.LOW)
        elif state == con_led_state.RED:
                GPIO.output(red_pin, GPIO.HIGH)
                GPIO.output(green_pin, GPIO.LOW)
        elif state == con_led_state.GREEN:
                GPIO.output(red_pin, GPIO.LOW)
                GPIO.output(green_pin, GPIO.HIGH)

def error(red_pin: int, green_pin: int, message: str):
        print(message)
        sys.stdout.flush()
        set_con_led(red_pin, green_pin, con_led_state.OFF)
        time.sleep(1)     
        GPIO.cleanup()
        sys.exit(1)

# Parse arguments
parser = argparse.ArgumentParser(description='Monitor and handle activity switch')
parser.add_argument(
        'SWITCH_GPIO',
        type=int,
        help='GPIO connected to switch'
)
parser.add_argument(
        'CON_LED_RED_GPIO',
        type=int,
        help='GPIO of red pin for connection LED'
)
parser.add_argument(
        'CON_LED_GREEN_GPIO',
        type=int,
        help='GPIO of green pin for connection LED'
)
args = parser.parse_args()

switch_pin = args.SWITCH_GPIO
red_pin = args.CON_LED_RED_GPIO
green_pin = args.CON_LED_GREEN_GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(switch_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(red_pin, GPIO.OUT)
GPIO.setup(green_pin, GPIO.OUT)

prev_state = GPIO.input(switch_pin)

while True:
        while not check_connection():
                set_con_led(red_pin, green_pin, con_led_state.RED)

        set_con_led(red_pin, green_pin, con_led_state.GREEN)

        curr_state = GPIO.input(switch_pin)
        if curr_state != prev_state:
                if curr_state == GPIO.LOW:
                        print("TUDO ist offen!")
                        sys.stdout.flush()
                elif curr_state == GPIO.HIGH:
                        print("TUDO ist geschlossen!")
                        sys.stdout.flush()
                prev_state = curr_state