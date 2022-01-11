import os
import sys
import pathlib
import time
import argparse
import configparser
import RPi.GPIO as GPIO

from enum import Enum
from urllib.request import urlopen

ADD_DATA_PATH = "/var/lib/switch_monitor"
SAVED_STATE_PATH = ADD_DATA_PATH + "/saved_state"

class con_led_state(Enum):
        OFF = 0
        RED = 1
        GREEN = 2

class activity(Enum):
        # Inverted because of pull-up
        clsd = 0
        opn = 1

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

def call_subservices(config: configparser.ConfigParser, activity: activity):
        for section in config.sections():
                for option in config[section]:
                        if activity == activity.opn and option == "openexec":
                                print("Executing " + config[section][option])
                                sys.stdout.flush()
                                os.system(config[section][option])
                        if activity == activity.clsd and option == "closedexec":
                                print("Executing " + config[section][option])
                                sys.stdout.flush()
                                os.system(config[section][option])

# --- MAIN --- #

# Parse arguments
parser = argparse.ArgumentParser(description='Monitor and handle activity switch')
parser.add_argument(
        '-c', '--config',
        default = os.path.dirname(os.path.realpath(__file__)) + '/config.ini',
        type = str,
        help = 'Path to configuration file'
)
args = parser.parse_args()
config = configparser.ConfigParser()
config.read(args.config)

# Create app data path if it does not exist
try:
        pathlib.Path(ADD_DATA_PATH).mkdir(parents=True, exist_ok=True)
except Exception as e:
        error(args.CON_LED_RED_GPIO, args.CON_LED_GREEN_GPIO, str(e))

# Set GPIO's
switch_pin = int(config['GPIO']['Switch'])
red_pin = int(config['GPIO']['ConLEDRed'])
green_pin = int(config['GPIO']['ConLEDGreen'])

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
                        call_subservices(config, activity.opn)
                elif curr_state == GPIO.HIGH:
                        call_subservices(config, activity.clsd)

                try:
                        save_state(SAVED_STATE_PATH, curr_state)
                except Exception as e:
                        error(red_pin, green_pin, str(e))
                        
                prev_state = curr_state
        
