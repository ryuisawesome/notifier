import requests
import time
import json
from datetime import datetime
import logging
import threading
from typing import List, Dict, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("username_checker.log"),
        logging.StreamHandler()
    ]
)

class UsernameChecker:
    def __init__(self):
        self.webhook_url = self._get_webhook_url()
        self.user_ids = self._get_user_ids()
        self.usernames_to_check = self.load_usernames_from_file()
        self.username_status = {username: "unknown" for username in self.usernames_to_check}
        self.username_available_time = {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.request_timeout = 2
        self.check_interval = 0.01
        self.rate_limit_delay = 1 

    def _get_webhook_url(self) -> str:
        """Safely get webhook URL from user input"""
        while True:
            url = input("Enter your Discord Webhook URL: ").strip()
            if url.startswith('https://discord.com/api/webhooks/'):
                return url
            print("Invalid webhook URL. Please enter a valid Discord webhook URL.")

    def _get_user_ids(self) -> List[str]:
        """Get Discord user IDs from user input"""
        ids_input = input("Enter Discord user IDs to ping (comma-separated, or press Enter for none): ").strip()
        if not ids_input:
            return []
        return [id.strip() for id in ids_input.split(',') if id.strip()]

    def load_usernames_from_file(self, filename: str = "usernames.txt") -> List[str]:
        """Load usernames from a file, creating it if it doesn't exist"""
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                usernames = [line.strip() for line in file.readlines() if line.strip()]
            logging.info(f"Loaded {len(usernames)} usernames from {filename}")
            return usernames
        except FileNotFoundError:
            logging.warning(f"{filename} not found. Creating an empty file.")
            with open(filename, 'w', encoding='utf-8') as file:
                pass
            return []
        except Exception as e:
            logging.error(f"Error reading {filename}: {e}")
            return []

    def save_username_to_file(self, username: str, filename: str = "available_usernames.txt"):
        """Save available usernames to a file"""
        try:
            with open(filename, 'a', encoding='utf-8') as file:
                file.write(f"{username} - {datetime.now().isoformat()}\n")
        except Exception as e:
            logging.error(f"Error saving username to {filename}: {e}")

    def send_discord_ping(self, username: str, message_type: str, duration: Optional[float] = None):
        """Send a notification to Discord"""
        user_mentions = " ".join([f"<@{user_id}>" for user_id in self.user_ids])
        
        if message_type == "available":
            message_content = f"{user_mentions} Username **{username}** is AVAILABLE!"
            self.save_username_to_file(username)
        elif message_type == "claimed":
            message_content = f"{user_mentions} Username **{username}** was claimed in {duration:.2f} seconds!"
        else:
            return
        
        message = {
            "content": message_content,
            "embeds": [{
                "title": f"Username {message_type.title()}",
                "description": f"Username **{username}** is now {message_type}",
                "color": 3066993 if message_type == "available" else 15158332,
                "timestamp": datetime.now().isoformat(),
                "footer": {"text": "Roblox Username Checker"}
            }]
        }
        
        try:
            response = self.session.post(self.webhook_url, json=message, timeout=self.request_timeout)
            response.raise_for_status()
            logging.info(f"Discord notification sent for: {username} ({message_type})")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending Discord notification for {username}: {e}")

    def check_username(self, username: str) -> Tuple[str, str]:
        """Check if a username is available on Roblox"""
        url = f"https://auth.roblox.com/v1/usernames/validate?Username={username}&Birthday=2000-01-01"
        try:
            response = self.session.get(url, timeout=self.request_timeout)
            response.raise_for_status()
            result = response.json()
            message = result.get("message", "")
            code = result.get("code", 0)
            
            if code == 3: 
                logging.warning("Rate limited. Waiting 0.02 seconds before continuing.")
                time.sleep(0.02)
                return self.check_username(username)
                
            return username, message
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed for {username}: {e}")
            return username, f"Request failed: {e}"
        except json.JSONDecodeError:
            logging.error(f"Failed to decode JSON response for {username}")
            return username, "Failed to decode JSON response"

    def check_all_usernames(self):
        """Check all usernames in the list"""
        if not self.usernames_to_check:
            logging.warning("No usernames to check. Add usernames to usernames.txt")
            return
            
        logging.info(f"Starting to check {len(self.usernames_to_check)} usernames")
        
        for username in self.usernames_to_check:
            name, msg = self.check_username(username)
            current_time = time.time()
            
            if msg == "Username is valid" and self.username_status[username] != "available":
                logging.info(f"Username '{name}' is now available!")
                self.username_status[username] = "available"
                self.username_available_time[username] = current_time
                self.send_discord_ping(username, "available")
            
            elif msg != "Username is valid" and self.username_status[username] == "available":
                duration = current_time - self.username_available_time[username]
                logging.info(f"Username '{name}' was claimed after {duration:.2f} seconds!")
                self.username_status[username] = "claimed"
                self.send_discord_ping(username, "claimed", duration)
            
            logging.debug(f"Checked {name}: {msg}")
            time.sleep(self.rate_limit_delay)

    def run(self):
        """Main loop to continuously check usernames"""
        logging.info("Starting Roblox Username Notifier...")
        
        while True:
            try:
                self.check_all_usernames()
                logging.info(f"Completed full check cycle. Waiting {self.check_interval} seconds before next cycle.")
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                logging.info("Script stopped by user")
                break
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                time.sleep(1)

if __name__ == "__main__":
    checker = UsernameChecker()
    checker.run()
