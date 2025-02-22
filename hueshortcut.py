import os
import time
import json
import requests
import keyboard
import logging
import argparse
from dotenv import load_dotenv

CONFIG_FILE = ".env"
# Dictionary to store the last known state of each device keyed by device_id.
device_states = {}

# Configure logging to output to the console.
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

def update_config_value(key, value):
    """Update a key-value pair in the .env configuration file."""
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            for line in f:
                if '=' in line:
                    k, v = line.strip().split("=", 1)
                    config[k] = v
    config[key] = value
    with open(CONFIG_FILE, "w") as f:
        for k, v in config.items():
            f.write(f"{k}={v}\n")

def register_hue_username(bridge_ip, device_type="hueshortcut#pc", timeout=30):
    """
    Registers with the Hue Bridge by prompting you to press the physical link button.
    Attempts registration until successful or until the timeout is reached.
    """
    url = f"http://{bridge_ip}/api"
    payload = {"devicetype": device_type}
    logging.info("Attempting to register with the Hue Bridge. Please press the link button on your bridge.")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.post(url, json=payload, timeout=5)
            result = response.json()
            logging.debug("Received registration response: %s", result)
            if isinstance(result, list) and "success" in result[0]:
                username = result[0]["success"]["username"]
                logging.info("Registration successful. Username: %s", username)
                return username
            else:
                error = result[0].get("error", {}).get("description", "Waiting for link button press...")
                logging.warning("Registration response: %s", error)
        except Exception as e:
            logging.exception("Error during registration: %s", e)
        time.sleep(2)
    
    logging.error("Failed to register with the Hue Bridge within the timeout period.")
    return None

def update_username():
    """
    Prompts to update the Hue API username.
    First asks if you want to use an existing username (and validates it),
    or perform automatic registration by pressing the link button.
    Then updates the configuration file.
    """
    if not os.path.exists(CONFIG_FILE):
        print("No configuration found. Run the full setup first.")
        return

    load_dotenv(CONFIG_FILE)
    bridge_ip = os.getenv("HUE_BRIDGE_IP")
    if not bridge_ip:
        print("HUE_BRIDGE_IP not found in configuration. Please run the full setup.")
        return

    choice = input("Do you want to use an existing username? (y/n): ").strip().lower()
    if choice == 'y':
        new_username = input("Enter your Hue API username: ").strip()
        test_url = f"http://{bridge_ip}/api/{new_username}/lights"
        try:
            response = requests.get(test_url, timeout=5)
            result = response.json()
            if isinstance(result, dict) and result:
                print("Username is valid.")
                update_config_value("HUE_USERNAME", new_username)
                return
            else:
                print("Invalid username or no devices found. Falling back to automatic registration.")
        except Exception as e:
            print("Error validating username:", e)
    
    print("Proceeding with automatic registration. Please press the link button on your Hue Bridge.")
    new_username = register_hue_username(bridge_ip)
    if new_username:
        update_config_value("HUE_USERNAME", new_username)
        print("Username updated successfully.")
    else:
        print("Failed to update username.")

def interactive_device_setup(bridge_ip, username):
    """
    Retrieves available devices from the Hue Bridge and allows the user
    to add multiple devices with individual hotkeys.
    Returns a list of device configurations.
    """
    url = f"http://{bridge_ip}/api/{username}/lights"
    try:
        response = requests.get(url)
        devices = response.json()  # dict: device_id -> device info
        logging.debug("Retrieved devices: %s", devices)
    except Exception as e:
        logging.exception("Error retrieving devices: %s", e)
        return None

    if not devices:
        logging.error("No devices found!")
        return None

    configured_devices = []
    while True:
        print("\nAvailable devices:")
        for dev_id, info in devices.items():
            print(f"ID: {dev_id} - Name: {info.get('name', 'Unknown')} (Type: {info.get('type', 'N/A')})")
        selected_device = input("Enter the ID of the device you want to add (or press Enter to finish): ").strip()
        if not selected_device:
            break
        if selected_device not in devices:
            print("Invalid device ID. Please try again.")
            continue
        device_name = devices[selected_device].get("name", "Unknown")
        hotkey = input(f"Enter your desired keyboard shortcut for '{device_name}' (e.g., ctrl+shift+l): ").strip()
        configured_devices.append({"device_id": selected_device, "hotkey": hotkey, "name": device_name})
        cont = input("Would you like to add another device? (y/n): ").strip().lower()
        if cont != 'y':
            break
    return configured_devices

def interactive_setup():
    """
    Interactive configuration:
    - Prompts for the Hue Bridge IP address.
    - Asks if you want to use an existing Hue API username or register automatically.
    - Invokes device setup to add multiple devices with individual hotkeys.
    - Saves HUE_BRIDGE_IP, HUE_USERNAME, and DEVICES to the .env file.
    """
    bridge_ip = input("Enter your Hue Bridge IP address: ").strip()

    choice = input("Do you want to use an existing Hue API username? (y/n): ").strip().lower()
    if choice == 'y':
        username = input("Enter your Hue API username: ").strip()
        test_url = f"http://{bridge_ip}/api/{username}/lights"
        try:
            response = requests.get(test_url, timeout=5)
            result = response.json()
            if isinstance(result, dict) and result:
                print("Username is valid. Using provided username.")
            else:
                print("Provided username is not valid. Falling back to automatic registration.")
                username = register_hue_username(bridge_ip)
        except Exception as e:
            print("Error validating username:", e)
            username = register_hue_username(bridge_ip)
    else:
        username = register_hue_username(bridge_ip)

    if not username:
        logging.error("Could not register with the Hue Bridge.")
        return False

    devices_config = interactive_device_setup(bridge_ip, username)
    if not devices_config or len(devices_config) == 0:
        logging.error("No devices configured.")
        return False

    with open(CONFIG_FILE, "w") as f:
        f.write(f"HUE_BRIDGE_IP={bridge_ip}\n")
        f.write(f"HUE_USERNAME={username}\n")
        f.write(f"DEVICES={json.dumps(devices_config)}\n")
    logging.info("Configuration saved to %s", CONFIG_FILE)
    return True

def edit_devices():
    """
    Allows editing of the configured devices.
    Loads the current HUE_BRIDGE_IP and HUE_USERNAME, then re-runs the interactive device setup.
    Updates the DEVICES configuration in the .env file.
    """
    if not os.path.exists(CONFIG_FILE):
        logging.error("Configuration file not found. Run the script without '--edit' first.")
        return

    load_dotenv(CONFIG_FILE)
    bridge_ip = os.getenv("HUE_BRIDGE_IP")
    username = os.getenv("HUE_USERNAME")
    if not (bridge_ip and username):
        logging.error("Missing HUE_BRIDGE_IP or HUE_USERNAME in configuration. Cannot edit devices.")
        return

    new_devices_config = interactive_device_setup(bridge_ip, username)
    if not new_devices_config or len(new_devices_config) == 0:
        logging.error("No devices configured.")
        return

    # Read current configuration to preserve other keys.
    config = {}
    with open(CONFIG_FILE, "r") as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split("=", 1)
                config[key] = value
    config["DEVICES"] = json.dumps(new_devices_config)

    with open(CONFIG_FILE, "w") as f:
        for key, value in config.items():
            f.write(f"{key}={value}\n")
    logging.info("Device configuration updated.")

def initialize_state(bridge_ip, username, device_id):
    """
    Retrieves the current state of a device and stores it in the global device_states dictionary.
    """
    global device_states
    state_url = f"http://{bridge_ip}/api/{username}/lights/{device_id}"
    try:
        res = requests.get(state_url)
        data = res.json()
        state = data["state"].get("on", False)
        logging.info("Initial state for device %s: %s", device_id, "ON" if state else "OFF")
        device_states[device_id] = state
    except Exception as e:
        logging.exception("Error initializing state for device %s: %s", device_id, e)
        device_states[device_id] = False

def toggle_device(bridge_ip, username, device_id):
    """
    Toggles the state of the given device using the stored state,
    then confirms the new state via a GET request.
    """
    global device_states
    current_state = device_states.get(device_id, False)
    new_state = not current_state
    logging.info("Toggling device %s to %s", device_id, "ON" if new_state else "OFF")
    command_url = f"http://{bridge_ip}/api/{username}/lights/{device_id}/state"
    payload = {"on": new_state}
    try:
        res = requests.put(command_url, json=payload)
        logging.debug("Response from bridge: %s", res.json())
        device_states[device_id] = new_state
        # Confirm the new state.
        confirm_url = f"http://{bridge_ip}/api/{username}/lights/{device_id}"
        confirm_res = requests.get(confirm_url)
        confirm_data = confirm_res.json()
        confirmed_state = confirm_data["state"].get("on", False)
        logging.info("Confirmed state for device %s: %s", device_id, "ON" if confirmed_state else "OFF")
    except Exception as e:
        logging.exception("Error toggling device %s: %s", device_id, e)

def main():
    parser = argparse.ArgumentParser(description="Hue Shortcut Script with Multiple Devices")
    parser.add_argument("--edit", action="store_true", help="Edit the configured devices")
    parser.add_argument("--username", action="store_true", help="Update the Hue API username and reconnect to the bridge")
    args = parser.parse_args()

    if args.username:
        update_username()
        return

    if args.edit:
        edit_devices()
        return

    # Run interactive setup if configuration does not exist.
    if not os.path.exists(CONFIG_FILE):
        if not interactive_setup():
            return

    load_dotenv(CONFIG_FILE)
    bridge_ip = os.getenv("HUE_BRIDGE_IP")
    username = os.getenv("HUE_USERNAME")
    devices_str = os.getenv("DEVICES")
    if not (bridge_ip and username and devices_str):
        logging.error("Missing configuration values. Please re-run the setup.")
        return

    try:
        devices = json.loads(devices_str)
    except Exception as e:
        logging.exception("Error parsing devices configuration: %s", e)
        return

    if not devices or len(devices) == 0:
        logging.error("No devices configured. Please run the setup again.")
        return

    # Initialize state for each configured device and bind their hotkeys.
    for device in devices:
        device_id = device["device_id"]
        initialize_state(bridge_ip, username, device_id)
        hotkey = device["hotkey"]
        logging.info("Registering hotkey %s for device %s (%s)", hotkey, device_id, device.get("name", "Unknown"))
        keyboard.add_hotkey(hotkey, lambda device_id=device_id: toggle_device(bridge_ip, username, device_id))

    logging.info("Monitoring for hotkey presses. Press ESC to exit.")
    keyboard.wait("esc")

if __name__ == '__main__':
    main()
