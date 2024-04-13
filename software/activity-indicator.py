#!/usr/bin/env python3

# Copyright (C) 2022 Patrick Pedersen, TUDO Makerspace

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Author: Patrick Pedersen <ctx.xda@gmail.com>
# Description:
#       The following script contains the main code for the activity indicator.
#       It is executed as a background service by the activity-indicator systemd
#       service and monitors the activity switch, reports if a connection to the
#       internet is available, and executes a list of sub-services specified in the
#       config file.
#       This script must be run by the activity-indicator systemd service, and should not
#       be run manually. The GPIOs for the activity switch, as well as the connection
#       indicator LED must be specified in the config file.

from asyncio import wait_for
import os
import sys
import pathlib
import time
import argparse
import configparser
import RPi.GPIO as GPIO

from enum import Enum
from ping3 import ping

# List of possible candidates to ping to check for internet connection
# Redundancy is good in case one of the candidates is down
# or much more likely, the uni's firewall is having a bad day
# again?
ping_candidates = [
    "8.8.8.8",
    "www.google.com",
    "google.com",
    "www.tu-berlin.de",
    "www.yahoo.com",
    "www.bing.com",
]

# Constants
SW_VER = "1.2.1"
AUTHOR = "Patrick Pedersen <ctx.xda@gmail.com>, TU-DO Makerspace <tu-do.net>"
LICENSE = "GPLv3"
SOURCE_CODE = "https://github.com/TU-DO-Makerspace/Activity-Indicator"

ADD_DATA_PATH = "/var/lib/activity-indicator"  # App data path
SAVED_STATE_PATH = ADD_DATA_PATH + "/saved_state"  # Path to save states to
RESET_WIFI_TIMEOUT = 60  # Seconds


# Enum for connection indicator LED
class con_led_state(Enum):
    OFF = 0
    RED = 1
    GREEN = 2


# Enum for possible activity states
class activity(Enum):
    CLOSED = 0
    OPEN = 1


# Wrapper for print to work with journalctl logs
# -
# msg - Message to be printed
def print_journalctl(msg):
    print(msg)
    sys.stdout.flush()  # Needed, else print won't appear in journalctl log


# Checks if internet connection is available
# -
# Returns True if connection is available, False otherwise
def check_connection():
    for candidate in ping_candidates:
        ret = ping(candidate, timeout=1)
        if ret:
            return True
    return False


# Sets the connection indicator LED
# -
# red_pin: GPIO pin connected to red LED
# green_pin: GPIO pin connected to green LED
# state: con_led_state enum, specifying the color of the LED
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


# Prints error message, blinks the connection LED green and red 3x,
# cleans up the GPIOs and exits
# -
# red_pin: GPIO pin connected to red LED
# green_pin: GPIO pin connected to green LED
# message: error message to print
def error(red_pin: int, green_pin: int, message: str):
    print_journalctl("FATAL ERROR: " + message)

    for i in range(3):
        set_con_led(red_pin, green_pin, con_led_state.GREEN)
        time.sleep(0.5)
        set_con_led(red_pin, green_pin, con_led_state.OFF)
        time.sleep(0.5)
        set_con_led(red_pin, green_pin, con_led_state.RED)
        time.sleep(0.5)
        set_con_led(red_pin, green_pin, con_led_state.OFF)
        time.sleep(0.5)

    GPIO.cleanup()
    sys.exit(1)


# Converts a GPIO state to an activity state
# Since the switch is connected via a pull-up resistor,
# a HIGH input means the switch is set to CLOSED, and a LOW
# input means the switch is set to OPEN
# -
# state: GPIO state to convert
# -
# Returns the activity state
def GPIO_to_activity(state: int):
    if state == GPIO.LOW:
        return activity.OPEN
    else:
        return activity.CLOSED


# Saves the current state of the activity switch to a file.
# This is used to retrieve/remember the previous state of the
# Activity Indicator in case of an unexpected shutdown or program
# crash.
# -
# path: path to the file to save the state to
# state: the state to save (GPIO.LOW or GPIO.HIGH)
def save_state(path: str, state: activity):
    with open(path, "w") as f:
        f.write(state.name)


# Retrieves the saved state of the activity switch from the file
# -
# path: path to the file to read the state from
# -
# Returns the activity status from the file
def saved_state(path: str):
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        content = f.read()
        if content == activity.OPEN.name:
            return activity.OPEN
        elif content == activity.CLOSED.name:
            return activity.CLOSED
        else:
            print_journalctl("Unknown saved state: " + content)
            return None


# Calls all sub-services specified in the config file
# If the provided activity is open, the 'openexec' command is executed,
# If the provided activity is closed, the 'closedexec' command is executed
#  -
# config: configparser object containing the config file
# activity: activity enum, specifying new activity state
# -
# Returns True if all subservices executed successfully, False if one or more subservices failed
def call_subservices(config: configparser.ConfigParser, activity: activity):
    success = True
    for section in config.sections():
        for option in config[section]:
            ret = 0
            service = section + ": " + option + ": " + config[section][option]
            if activity == activity.OPEN and option == "openexec":
                print_journalctl("Executing: " + service)
                ret = os.system(config[section][option])
            elif activity == activity.CLOSED and option == "closedexec":
                print_journalctl("Executing: " + service)
                ret = os.system(config[section][option])

            if ret != 0:
                print("Unexpected error while calling subservice: " + service)
                success = False
    return success


# Waits until a connection to the internet is available
# If a connection is available, true is returned.
# If a connection is not available after the provided timeout
# in seconds, false is returned.
#
# NOTE: This function will block until a connection is available
# -
# timeout: timeout in seconds
# -
# Returns True if a connection is available, False if a connection is not available after the timeout
def wait_for_connection(timeout_s: int):
    timeout = time.time() + timeout_s
    while not check_connection():
        if time.time() >= timeout:
            return False
    return True


# Handles WiFi connection related tasks, such as
# - Checking if a connection is available
# - Setting the connection indicator LED
# - Attempting to reconnect to the WiFi network
#
# If the functon fails to connect to the WiFi network after 60 seconds, it will
# raise a ConnectionError exception.
#
# NOTE: This function will block until a connection is available
# -
# red_pin: GPIO pin connected to red LED
# green_pin: GPIO pin connected to green LED
# -
def handle_connection(red_pin: int, green_pin: int):
    if not check_connection():
        set_con_led(red_pin, green_pin, con_led_state.RED)
        if not wait_for_connection(RESET_WIFI_TIMEOUT):
            raise ConnectionError("No connection available after timeout")
    set_con_led(red_pin, green_pin, con_led_state.GREEN)


# Resets the WiFi connection by restarting the WiFi interface
def reset_wifi():
    os.system("ifconfig wlan0 down")
    os.system("ifconfig wlan0 up")


# --- MAIN --- #

# Parse arguments
parser = argparse.ArgumentParser(description="Handles the activity indicator")
parser.add_argument(
    "-c",
    "--config",
    default=os.path.dirname(os.path.realpath(__file__)) + "/activity-indicator.ini",
    type=str,
    help="Path to configuration file",
)
args = parser.parse_args()
config = configparser.ConfigParser()
config.read(args.config)

# Boot message
print("=== TU-DO Activity Indicator ===")
print("Version:\t" + SW_VER)
print("Author:\t\t" + AUTHOR)
print("License:\t" + LICENSE)
print("Source code:\t" + SOURCE_CODE)

# Create app data path if it does not exist
try:
    pathlib.Path(ADD_DATA_PATH).mkdir(parents=True, exist_ok=True)
except Exception as e:
    error(args.CON_LED_RED_GPIO, args.CON_LED_GREEN_GPIO, str(e))

# Set GPIO's
switch_pin = int(config["GPIO"]["Switch"])
red_pin = int(config["GPIO"]["ConLEDRed"])
green_pin = int(config["GPIO"]["ConLEDGreen"])

GPIO.setmode(GPIO.BCM)
GPIO.setup(switch_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(red_pin, GPIO.OUT)
GPIO.setup(green_pin, GPIO.OUT)

# Check if saved state data exists, create if not
if saved_state(SAVED_STATE_PATH) == None:
    try:
        save_state(SAVED_STATE_PATH, GPIO_to_activity(GPIO.input(switch_pin)))
    except Exception as e:
        error(red_pin, green_pin, str(e))

# Compare to last saved state
prev_state = saved_state(SAVED_STATE_PATH)

# Used to check if we've successfully re-established internet connection
prev_wifi_state = True

# Main loop
while True:
    # Check connection
    try:
        handle_connection(red_pin, green_pin)
    except ConnectionError as e:
        print_journalctl(
            "Failed to establish connection, resetting WiFi interface and retrying..."
        )
        reset_wifi()
        prev_wifi_state = False
        continue

    if not prev_wifi_state:
        print_journalctl("Successfully re-established connection!")
        prev_wifi_state = True

    # Fetch position of switch
    curr_state = GPIO_to_activity(GPIO.input(switch_pin))

    # Activity changed, call subservices
    if curr_state != prev_state:
        try:
            # Call subservices
            print_journalctl(
                "Activity changed to: " + str(curr_state.name) + ", calling subservices"
            )
            ret = call_subservices(config, curr_state)

            # Save activity state to file
            prev_state = curr_state
            save_state(SAVED_STATE_PATH, prev_state)

            if not ret:
                error(red_pin, green_pin, "One or more subservices failed")

            print_journalctl("All subservices executed successfully")

        except Exception as e:
            error(red_pin, green_pin, str(e))
