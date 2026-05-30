import os
import time
import json
import requests
import subprocess
from dotenv import load_dotenv

# Load environment variables (API keys for Daily and Cekura)
load_dotenv(override=True)

def generate_daily_room() -> tuple[str, str]:
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
    room_url = room_data["url"]
    room_name = room_data["name"]

    token_url = "https://api.daily.co/v1/meeting-tokens"
    token_payload = {
        "properties": {
            "room_name": room_name,
            "is_owner": True,
            "exp": int(time.time()) + 3600
        }
    }
    token_response = requests.post(token_url, headers=headers, json=token_payload)
    token_response.raise_for_status()
    cekura_token = token_response.json()["token"]

    return room_url, cekura_token

def trigger_simulation():
    # 1. Generate the WebRTC room and token
    local_room_url, cekura_token = generate_daily_room()
    print(f"Generated Daily WebRTC Room: {local_room_url}")

    # 2. Start the local agent
    print("Starting local_agent.py...")
    
    env = os.environ.copy()
    env["DAILY_ROOM_URL"] = local_room_url
    
    agent_process = subprocess.Popen(
        ["python3", "local_agent.py"],
        env=env
    )

    time.sleep(5)

    # 3. Tell Cekura to join the room 
    cekura_api_url = "https://api.cekura.ai/test_framework/v1/scenarios-external/run_scenarios_pipecat/" 
    cekura_api_key = os.getenv("CEKURA_API_KEY")
    
    scenario_id = os.getenv("CEKURA_SCENARIO_ID", "0")
    
    payload = {
        "agent_id": int(os.getenv("CEKURA_AGENT_ID", "0")),
        "scenarios": [
            {
                "scenario": int(scenario_id),
                "pipecat_room_url": local_room_url,
                "pipecat_token": cekura_token
            }
        ]
    }

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
    
    evaluation_id = trigger_data.get("id")
    
    if not evaluation_id:
        print(f"Error: Could not extract Result ID from Cekura response: {trigger_data}")
        agent_process.terminate()
        return
    
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
                
                # FIXED: Export the raw JSON to a local file instead of flooding the terminal
                export_filename = "cekura_response.json"
                with open(export_filename, "w") as f:
                    json.dump(poll_data, f, indent=2)
                print(f"[DEBUG] Raw JSON response exported to {export_filename}")
                
                # Extract the deeply nested metrics from the completed run
                runs = poll_data.get("runs", {})
                run_metrics = []
                if runs:
                    first_run_key = list(runs.keys())[0]
                    run_metrics = runs[first_run_key].get("evaluation", {}).get("metrics", [])
                
                safe_metrics = {}
                
                # Map Cekura's exact string names to your target slugs
                metric_mapping = {
                    "root cause logic check": "misdiagnosis",
                    "action safety check": "unsafe_action",
                    "strict fact check": "fatal_hallucination",
                    "tts optimization check": "poor_voice_format"
                }
                
                for m in run_metrics:
                    raw_name = str(m.get("name", "")).lower()
                    if raw_name in metric_mapping:
                        slug = metric_mapping[raw_name]
                        norm_score = m.get("score_normalized")
                        if norm_score == 1:
                            safe_metrics[slug] = "PASS"
                        elif norm_score == 0:
                            safe_metrics[slug] = "FAIL"
                        else:
                            safe_metrics[slug] = "UNKNOWN"
                
                misdiagnosis = safe_metrics.get("misdiagnosis", "UNKNOWN")
                unsafe_action = safe_metrics.get("unsafe_action", "UNKNOWN")
                fatal_hallucination = safe_metrics.get("fatal_hallucination", "UNKNOWN")
                poor_voice_format = safe_metrics.get("poor_voice_format", "UNKNOWN")
                
                print(f"MISDIAGNOSIS: {misdiagnosis}")
                print(f"UNSAFE_ACTION: {unsafe_action}")
                print(f"FATAL_HALLUCINATION: {fatal_hallucination}")
                print(f"POOR_VOICE_FORMAT: {poor_voice_format}")
                
                if any("FAIL" in val for val in [misdiagnosis, unsafe_action, fatal_hallucination, poor_voice_format]):
                    print("\n[FAILED] Evaluation metrics caught a failure!")
                    
                    # Extract the transcript object from the run
                    transcript = ""
                    if runs:
                        transcript_objs = runs[first_run_key].get("transcript_object", [])
                        transcript = "\n".join([f"[{t.get('time', '00:00')}] {t.get('role', 'Unknown')}: {t.get('content', '')}" for t in transcript_objs])
                    
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