import requests
import time
import json
from datetime import datetime

DISCORD_WEBHOOK_URL = input("Enter your Discord Webhook URL: ")
DISCORD_USER_IDS = [] replace with ur discord id

def load_usernames_from_file(filename="usernames.txt"):
    try:
        with open(filename, 'r') as file:
            usernames = [line.strip() for line in file.readlines() if line.strip()]
        return usernames
    except FileNotFoundError:
        print(f"Error: {filename} not found. Creating an empty file.")
        with open(filename, 'w') as file:
            pass
        return []
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return []

usernames_to_check = load_usernames_from_file()
username_status = {username: "unknown" for username in usernames_to_check}
username_available_time = {}

def send_discord_ping(username, message_type, duration=None):
    user_mentions = " ".join([f"<@{user_id}>" for user_id in DISCORD_USER_IDS])
    
    if message_type == "available":
        message_content = f"{user_mentions} Username **{username}** is AVAILABLE!"
    elif message_type == "claimed":
        message_content = f"{user_mentions} Username **{username}** was claimed in {duration:.6f} seconds!"
    else:
        return
    
    message = {"content": message_content}
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=message)
        response.raise_for_status()
        print(f"Discord ping sent for: {username} ({message_type})")
    except requests.exceptions.RequestException as e:
        print(f"Error sending Discord ping for {username}: {e}")

def check_username(username):
    url = f"https://auth.roblox.com/v1/usernames/validate?Username={username}&Birthday=2000-01-01"
    try:
        response = requests.get(url)
        response.raise_for_status()
        result = response.json()
        message = result.get("message", "")
        return username, message
    except requests.exceptions.RequestException as e:
        return username, f"Request failed: {e}"
    except json.JSONDecodeError:
        return username, "Failed to decode JSON response"

if __name__ == "__main__":
    print("Starting notifier...")
    print(f"Loaded {len(usernames_to_check)} usernames from file")
    
    while True:
        for username in usernames_to_check:
            name, msg = check_username(username)
            current_time = time.time()
            
            if msg == "Username is valid" and username_status[username] != "available":
                print(f"Username '{name}' is now available!")
                username_status[username] = "available"
                username_available_time[username] = current_time
                send_discord_ping(username, "available")
            
            elif msg != "Username is valid" and username_status[username] == "available":
                duration = current_time - username_available_time[username]
                print(f"Username '{name}' was claimed after {duration:.6f} seconds!")
                username_status[username] = "claimed"
                send_discord_ping(username, "claimed", duration)
            
            print(f"Checking {name}: {msg}")
            
            time.sleep(1)
