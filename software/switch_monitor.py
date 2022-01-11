import os
import sys
import pathlib
import time
import argparse
import RPi.GPIO as GPIO

from enum import Enum
from urllib.request import urlopen

ADD_DATA_PATH = "/var/lib/switch_monitor"
SAVED_STATE_PATH = ADD_DATA_PATH + "/saved_state"

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

def save_state(path: str, state:int):
        with open(path, 'w') as f:
                f.write(str(state))

def saved_state(path: str):
        if not os.path.exists(path):
                return None
        with open(path, 'r') as f:
                content = f.read()
                if content != str(GPIO.LOW) and content != str(GPIO.HIGH):
                        print("Invalid saved state, overwriting")
                        sys.stdout.flush()
                        return None
                return int(content)

# --- MAIN --- #

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

# Create app data path if it does not exist
try:
        pathlib.Path(ADD_DATA_PATH).mkdir(parents=True, exist_ok=True)
except Exception as e:
        error(args.CON_LED_RED_GPIO, args.CON_LED_GREEN_GPIO, str(e))

# Set GPIO's
switch_pin = args.SWITCH_GPIO
red_pin = args.CON_LED_RED_GPIO
green_pin = args.CON_LED_GREEN_GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(switch_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(red_pin, GPIO.OUT)
GPIO.setup(green_pin, GPIO.OUT)

# Check if saved state data exists, create if not
if saved_state(SAVED_STATE_PATH) == None:
        try:
                save_state(SAVED_STATE_PATH, GPIO.input(switch_pin))
        except Exception as e:
                error(red_pin, green_pin, str(e))

# Compare to last saved state
prev_state = saved_state(SAVED_STATE_PATH)

# Main loop
while True:
        # Check if connection is available
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

                try:
                        save_state(SAVED_STATE_PATH, curr_state)
                except Exception as e:
                        error(red_pin, green_pin, str(e))
                        
                prev_state = curr_state
        
