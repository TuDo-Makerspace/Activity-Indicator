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

import os
import sys
import pathlib
import time
import argparse
import configparser
import RPi.GPIO as GPIO

from enum import Enum
from ping3 import ping

# Constants
ADD_DATA_PATH = "/var/lib/activity-indicator" # App data path
SAVED_STATE_PATH = ADD_DATA_PATH + "/saved_state" # Path to save states to

# Enum for connection indicator LED
class con_led_state(Enum):
	OFF = 0
	RED = 1
	GREEN = 2

# Enum for possible activity states
class activity(Enum):
	clsd = 0
	opn = 1

def print_journalctl(msg):
	print(msg)
	sys.stdout.flush()

# Checks if internet connection is available
# -
# Returns True if connection is available, False otherwise
def check_connection():
	ret = ping('google.com')
	return ret != None and ret != False

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

# Prints error message, blinks the connection LED green and red 3x, cleans up the GPIOs and exits
# -
# red_pin: GPIO pin connected to red LED
# green_pin: GPIO pin connected to green LED
# message: error message to print
def error(red_pin: int, green_pin: int, message: str):
	print_journalctl(message)

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

# Saves the current state of the activity switch to a file.
# This is used to retrieve previous states in case of a unexpected shutdown
# or program crash.
# -
# path: path to the file to save the state to
# state: the state to save (GPIO.LOW or GPIO.HIGH)
def save_state(path: str, state:int):
	with open(path, 'w') as f:
		f.write(str(state))

# Retrieves the saved state of the activity switch from the file
# -
# path: path to the file to read the state from
def saved_state(path: str):
	if not os.path.exists(path):
		return None
	with open(path, 'r') as f:
		content = f.read()
		if content != str(GPIO.LOW) and content != str(GPIO.HIGH):
			print_journalctl("Invalid saved state, overwriting")
			return None
		return int(content)

# Calls all sub-services specified in the config file
# If the provided activity is open, the 'openexec' command is executed,
# If the provided activity is closed, the 'closedexec' command is executed
#  -
# config: configparser object containing the config file
# activity: activity enum, specifying new activity state
def call_subservices(config: configparser.ConfigParser, activity: activity):
	for section in config.sections():
		for option in config[section]:
			ret = 0
			subprocess = section + ": " + option + ": " + config[section][option]
			if activity == activity.opn and option == "openexec":
				print_journalctl("Executing: " + subprocess)
				ret = os.system(config[section][option])
			elif activity == activity.clsd and option == "closedexec":
				print_journalctl("Executing: " + subprocess)
				ret = os.system(config[section][option])

			if ret != 0:
				return subprocess

	return ""

# --- MAIN --- #

# Parse arguments
parser = argparse.ArgumentParser(description='Handles the activity indicator')
parser.add_argument(
	'-c', '--config',
	default = os.path.dirname(os.path.realpath(__file__)) + '/activity-indicator.ini',
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

	# Activity changed, call subservices
	if curr_state != prev_state:
		try:
			ret = True

			if curr_state == GPIO.LOW:
				print_journalctl("Activity changed to OPEN, calling subservices")
				ret = call_subservices(config, activity.opn)
			elif curr_state == GPIO.HIGH:
				print_journalctl("Activity changed to CLOSED, calling subservices")
				ret = call_subservices(config, activity.clsd)

			# Save activity state to file
			prev_state = curr_state
			save_state(SAVED_STATE_PATH, prev_state)

			if ret != "":
				error(red_pin, green_pin, "Unexpected error while calling subservice: " + ret)
			
			print_journalctl("All subservices executed successfully")

		except Exception as e:
			error(red_pin, green_pin, str(e))