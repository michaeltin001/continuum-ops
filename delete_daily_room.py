import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

def delete_daily_room():
    daily_api_key = os.getenv("DAILY_API_KEY")
    if not daily_api_key:
        print("Error: DAILY_API_KEY environment variable is missing in .env")
        return

    room_input = input("Enter the Daily room URL or name to delete: ").strip()
    # Extract just the room name if the full URL was pasted
    room_name = room_input.split("/")[-1]
    
    url = f"https://api.daily.co/v1/rooms/{room_name}"
    headers = {"Authorization": f"Bearer {daily_api_key}"}
    
    print(f"Attempting to delete room: {room_name}...")
    response = requests.delete(url, headers=headers)
    if response.status_code == 200:
        print("Successfully deleted room!")
    else:
        print(f"Failed to delete room (Status {response.status_code}): {response.text}")

if __name__ == "__main__":
    delete_daily_room()