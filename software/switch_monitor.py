import argparse
import sys
import RPi.GPIO as GPIO

# Parse arguments
parser = argparse.ArgumentParser(description='Monitor and handle activity switch')
parser.add_argument(
        'GPIO',
        type=int,
        help='GPIO connected to switch'
)
args = parser.parse_args()

switch_pin = args.GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(switch_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

prev_state = GPIO.input(switch_pin)

sys.stdout.flush()

while True:
        curr_state = GPIO.input(switch_pin)
        if curr_state != prev_state:
                if curr_state == GPIO.LOW:
                        print("TUDO ist offen!")
                        sys.stdout.flush()
                elif curr_state == GPIO.HIGH:
                        print("TUDO ist geschlossen!")
                        sys.stdout.flush()
                prev_state = curr_state