from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import os

def generate_string():
    print("=== Telegram Session String Generator ===")
    api_id = input("Enter your API ID: ")
    api_hash = input("Enter your API HASH: ")

    with TelegramClient(StringSession(), api_id, api_hash) as client:
        print("\n=== YOUR SESSION STRING ===")
        print(client.session.save())
        print("===========================")
        print("\nCopy the string above and save it as an environment variable named 'SESSION_STRING' in Render.")

if __name__ == "__main__":
    generate_string()
