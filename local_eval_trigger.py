import os
import time
import requests
import subprocess
from dotenv import load_dotenv

# Load environment variables (API keys for Daily and Cekura)
load_dotenv(override=True)

def generate_daily_room() -> str:
    daily_api_key = os.getenv("DAILY_API_KEY")
    if not daily_api_key:
        raise ValueError("DAILY_API_KEY environment variable is missing in .env")

    url = "https://api.daily.co/v1/rooms"
    headers = {
        "Authorization": f"Bearer {daily_api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "properties": {
            "exp": int(time.time()) + 3600
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    room_data = response.json()
    return room_data["url"]

def trigger_simulation():
    # 1. Generate the WebRTC room
    local_room_url = generate_daily_room()
    print(f"Generated Daily WebRTC Room: {local_room_url}")

    # 2. Start the local agent (FIXED: Passed URL via Environment Variable)
    print("Starting local_agent.py...")
    
    # Copy current environment and inject the Daily Room URL
    env = os.environ.copy()
    env["DAILY_ROOM_URL"] = local_room_url
    
    agent_process = subprocess.Popen(
        ["python3", "local_agent.py"],
        env=env
    )

    time.sleep(5)

    # 3. Tell Cekura to join the room 
    cekura_api_url = "https://api.cekura.ai/test_framework/v1/scenarios/run_scenarios/" 
    cekura_api_key = os.getenv("CEKURA_API_KEY")
    
    scenario_id = os.getenv("CEKURA_SCENARIO_ID", "0")
    payload = {
        "scenarios": [int(scenario_id)],
        "agent_id": os.getenv("CEKURA_AGENT_ID"),
        "agent_number": os.getenv("CEKURA_AGENT_NUMBER", "+15555555555"),
        "connection_settings": {
            "pipecat_room_url": local_room_url
        }
    }

    # FIXED: Used Cekura's specific X-CEKURA-API-KEY header
    headers = {
        "X-CEKURA-API-KEY": cekura_api_key,
        "Content-Type": "application/json"
    }

    print("Triggering Cekura 'Stressed Engineer' Simulation...")
    response = requests.post(cekura_api_url, json=payload, headers=headers)
    
    if response.status_code not in [200, 201]:
        print(f"Failed to trigger Cekura (Status {response.status_code}): {response.text}")
        agent_process.terminate()
        return
        
    trigger_data = response.json()
    print(f"Simulation Triggered! Cekura is joining the room.")
    
    # Extract the ID safely based on Cekura's response structure
    if "runs" in trigger_data and len(trigger_data["runs"]) > 0:
        evaluation_id = trigger_data["runs"][0].get("id")
    elif isinstance(trigger_data, list) and len(trigger_data) > 0:
        evaluation_id = trigger_data[0].get("id")
    else:
        evaluation_id = trigger_data.get("id")
    
    # 4. Poll for Evaluation Scores
    print("Polling Cekura for evaluation scores...")
    poll_url = f"https://api.cekura.ai/test_framework/v1/results/{evaluation_id}/"
    evaluation_complete = False
    
    while not evaluation_complete:
        time.sleep(5)
        poll_response = requests.get(poll_url, headers=headers)
        
        if poll_response.status_code == 200:
            poll_data = poll_response.json()
            status = poll_data.get("status")
            
            if status == "completed":
                evaluation_complete = True
                print("\n--- Cekura Evaluation Complete ---")
                
                metrics = poll_data.get("metrics", {})
                safe_metrics = {k.lower(): v for k, v in metrics.items()}
                
                misdiagnosis = safe_metrics.get("misdiagnosis")
                unsafe_action = safe_metrics.get("unsafe_action")
                fatal_hallucination = safe_metrics.get("fatal_hallucination")
                poor_voice_format = safe_metrics.get("poor_voice_format")
                
                print(f"MISDIAGNOSIS: {misdiagnosis}")
                print(f"UNSAFE_ACTION: {unsafe_action}")
                print(f"FATAL_HALLUCINATION: {fatal_hallucination}")
                print(f"POOR_VOICE_FORMAT: {poor_voice_format}")
                
                if "FAIL" in [misdiagnosis, unsafe_action, fatal_hallucination, poor_voice_format]:
                    print("\n[FAILED] Evaluation metrics caught a failure!")
                    transcript = poll_data.get("transcript", "")
                    
                    print("\n--- Captured Transcript for Teacher-Critic Loop ---")
                    print(transcript)
                else:
                    print("\n[SUCCESS] Agent passed all metrics!")
                    
            elif status in ["failed", "error", "cancelled"]:
                print(f"Simulation encountered an internal error ({status}) and failed to complete.")
                break
            else:
                print(f"Status: {status}... continuing to poll.")
        elif poll_response.status_code == 404:
            print("Evaluation in progress, waiting for results to be generated...")
        else:
            print(f"Error polling Cekura (Status {poll_response.status_code}): {poll_response.text}")
            break
            
    print("Shutting down local_agent.py...")
    agent_process.terminate()
    agent_process.wait()

if __name__ == "__main__":
    trigger_simulation()