# **Continuum-Ops: Project Plan**

### Phase 1: 9:00 AM – 11:30 AM | The Transport & Brain (V0)

**Objective:**
*Deploy your pre-pulled NVIDIA NIM Llama 3 container on AWS. Set up the Pipecat + Daily pipeline using Deepgram and Cartesia providers. Initialize Logfire/Langsmith to trace the initial interactions. Connect Pipecat to the NIM endpoint. Ensure you can have a basic conversation about a "Database Connection Exhaustion" event.*

Your goal in this phase is to establish a working voice connection between your laptop microphone/speakers and your remote GPU instance.

**What you are doing on your AWS EC2 Instance:**

* **Execution:** Run your finalized `launch_infrastructure.py` to boot your On-Demand instance. SSH in, export your `NGC_API_KEY`, and spin up your container using `docker_run_nim.sh`.
* **Verification:** Ensure Port 8000 is listening by hitting `http://YOUR_EC2_IP:8000/v1/models` from your laptop browser.

**What files you are creating on your Pop!_OS Laptop:**

* **Create `local_agent.py`:** This is your primary application file. You will import `pipecat`, configure the Daily WebRTC transport, and initialize the Deepgram STT and Cartesia TTS services. For the precise implementation of connecting to a remote OpenAI-compatible endpoint, please see the LLM initialization block using a dummy API key and local IP in `bot-nemotron.py`. For setting up your pipeline with `SileroVADAnalyzer` and registering mock diagnostic tools using `ToolsSchema()`, reference the implementation in `bot-gpt.py`.
* **How you are modifying it:** You will instantiate Pipecat's `OpenAILLMService`. Because your NVIDIA NIM container acts as an OpenAI-compatible endpoint, you will change the `base_url` to point directly to your remote AWS instance (`http://YOUR_EC2_IP:8000/v1`) and use the new `Settings` parameter instead of the deprecated `params`.
* **The Code Structure:**

```python
# Inside local_agent.py
transport = DailyTransport(...)
stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
tts = CartesiaTTSService(api_key=os.getenv("CARTESIA_API_KEY"), voice_id="...")

llm = OpenAILLMService(
    api_key="mock-key", # Required by the class, but NIM doesn't enforce it locally
    settings=OpenAILLMService.Settings(
        model="meta/llama-3.1-8b-instruct",
        base_url=f"http://{EC2_IP}:8000/v1"
    )
)

pipeline = Pipeline([transport.input(), stt, llm, tts, transport.output()])

```

---

### Phase 2: 11:30 AM – 1:30 PM | The Simulation & Eval Harness

**Objective:**
*Integrate Cekura. Write 3–5 aggressive, highly technical simulation scripts. Implement Nemotron as your evaluator. Set strict rubrics for zero-tolerance for invented trace IDs or DB misdiagnoses. Run the simulation. Let the base model fail by confusing connection pool exhaustion with a DNS failure.*

Your goal here is to automate the test loop and verify that your evaluation model catches the base model's errors.

**What you are doing in the Cekura Web UI:**

* **Action:** Log into your Cekura dashboard. Create a new Scenario. Navigate to the **Metrics Builder** and paste the text rubrics we engineered (`MISDIAGNOSIS` and `UNSAFE_ACTION`) directly into their prompt fields. Set the judge model to Nemotron.

**What files you are creating on your Pop!_OS Laptop:**

* **Create `local_eval_trigger.py`:** A script that programmatically acts as the "Stressed Engineer."
* **How you are modifying it:** The script will use the standard Daily API to generate a temporary WebRTC room URL locally. It will pass that generated room URL to our `local_agent.py` to join. It will then send a POST request to Cekura's API, passing the pipecat_room_url in the payload. This tells the Cekura "Simulated Engineer" to join our locally generated room to start the test. It will wait for the agent to fail, capture the transcript, and poll Cekura for the evaluation scores. When configuring your WebRTC transport to join this room, you can copy the `SmallWebRTCRunnerArguments` block found inside the `bot(runner_args)` function in either `bot-gpt.py` or `bot-nemotron.py`.

* **The Code Structure:**
```python
import requests
import os

# 1. You generate this locally using the Daily API
local_room_url = "[https://your-domain.daily.co/hackathon-room-123](https://your-domain.daily.co/hackathon-room-123)" 

# 2. You tell Cekura to join it
cekura_api_url = "[https://api.cekura.ai/v1/scenarios/trigger](https://api.cekura.ai/v1/scenarios/trigger)" # (Check Cekura's exact endpoint docs on the day)

payload = {
    "agent_id": os.getenv("CEKURA_AGENT_ID"),
    "scenario_id": os.getenv("CEKURA_SCENARIO_ID"),
    "connection_settings": {
        "pipecat_room_url": local_room_url
    }
}

headers = {
    "Authorization": f"Bearer {os.getenv('CEKURA_API_KEY')}",
    "Content-Type": "application/json"
}

response = requests.post(cekura_api_url, json=payload, headers=headers)
print("Simulation Triggered! Cekura is joining the room:", response.json())
```

* **Verification:** Run the script and watch your terminal. Ensure that when the agent misdiagnoses the issue, Cekura correctly returns a JSON payload containing `{"MISDIAGNOSIS": "FAIL", "UNSAFE_ACTION": "FAIL"}`.

---

### Phase 3: 1:30 PM – 4:00 PM | The Auto-Improvement Loop (The Magic)

**Objective:**
*Write the Python logic to listen for Cekura test failures. When a failure is caught, trigger the Teacher-Critic loop to generate 15–30 curated synthetic examples in JSONL format based on the specific failure log. Pipe the JSONL from memory to S3 and trigger the AWS SSM command to start the LoRA fine-tune. Once training finishes, verify the NVIDIA NIM hot-swap has updated the active adapter.*

This is the core engineering block where you build the self-healing feedback engine.

**What files you are modifying on your AWS EC2 Instance:**

* **Modify `train_lora_boilerplate.py`:** You are turning the placeholder skeleton into an actual execution script.
* **How you are modifying it:** Add the `argparse` block to catch the incoming parameters. Import the Hugging Face `SFTTrainer` and set up the `TrainingArguments`. Hardcode an aggressive, fast execution configuration optimized for a tiny dataset:

```python
# Inside train_lora_boilerplate.py on EC2
training_args = TrainingArguments(
    output_dir=args.output_dir,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=1,
    learning_rate=2e-4,
    logging_steps=1,
    num_train_epochs=3, # Fast run over 30 examples
    fp16=True
)

```

**What files you are creating on your Pop!_OS Laptop:**

* **Create `orchestrator.py`:** This is the control tower that links your laptop to S3 and SSM.
* **How you are modifying it:** Write the data generation pipeline. When `local_eval_trigger.py` catches a `FAIL` from Cekura, `orchestrator.py` must automatically intercept the raw system log, bundle it with the `TEACHER_PROMPT`, and send it to Claude 3.5 Sonnet to output the 30 JSONL training pairs.
* **The Execution Pipeline:** 1. Claude returns JSONL string -> 2. Boto3 uploads string directly to S3 -> 3. Boto3 invokes `ssm_trigger.py` -> 4. Remote instance trains and dumps weights to `/opt/nim/loras/incident_fix`.


* **Verification:** Run the whole loop. Hit your `Super + L` hotkey to watch the remote NIM container logs. Within 10 seconds of the training script finishing, you should see the green log line showing the NIM engine dynamically hot-loading the new adapter matrix.

---

### Phase 4: 4:00 PM – 6:00 PM | Polish & Demo Prep

**Objective:**
*Run the full pipeline end-to-end to ensure the fine-tune actually fixes the failure from the morning session. Build a simple dashboard visually showing: P1 Alert -> Critical Misdiagnosis -> Nemotron Flag -> Fine-Tune Triggered -> System Healed. Record a backup video of the working loop. Submit by 6:00 PM.*

This block is about user experience, aesthetics, and building a failsafe for the live presentation.

**What files you are creating on your Pop!_OS Laptop:**

* **Create `reset_environment.py`:** This hooks up to your `Super + R` hotkey.
* **How you are modifying it:** It needs to send an SSM command to the remote instance to delete the `/opt/nim/loras/incident_fix` directory, forcing the NVIDIA NIM container to drop the fine-tuned adapter and reset back to the "dumb" base model. This allows you to reset your environment instantly between judge tables.
* **Create `visual_logs.py`:** A visual wrapper module.
* **How you are modifying it:** Use the `rich` or `colorama` libraries to intercept your standard stdout prints from `orchestrator.py`. Format them with explicit colors matching your demo script (`[FAILED]` in bold red, `[HOT-SWAP SUCCESS]` in flashing bright green).

---

### Summary of Your Live Directory Structure

| File Name | Location | Purpose |
| --- | --- | --- |
| `launch_infrastructure.py` | Local Laptop | One-click On-Demand EC2 instantiation with dynamic IP firewalling. |
| `local_agent.py` | Local Laptop | Pipecat audio routing engine using Deepgram, Cartesia, and remote NIM. |
| `local_eval_trigger.py` | Local Laptop | Kicks off the Cekura simulation turns and parses evaluation webhooks. |
| `orchestrator.py` | Local Laptop | The control tower. Intercepts Cekura failures, prompts Claude for data, and orchestrates the upload/trigger flow. |
| `ssm_trigger.py` | Local Laptop | The AWS Boto3 utility module imported by the orchestrator to fire the remote execution command across the internet. |
| `visual_logs.py (NOT NEEDED ANYMORE)` | Local Laptop | The UI wrapper module imported by your scripts to format terminal outputs with colors (e.g., Flashing Red for FAILED). |
| `reset_environment.py` | Local Laptop | Wipes remote adapters to cleanly reset the live demo state via `Super + R`. |
| `.env` | Local Laptop | Holds all your API keys (Anthropic, Deepgram, AWS, etc.). *Never commit this to GitHub.* |
| `requirements.txt` | Local Laptop | Your Python dependency manifest (`pipecat-ai`, `boto3`, `requests`, `rich`, etc.). |
| `continuum-key.pem` | Local Laptop | Your AWS SSH key (must be set to `chmod 400` permissions). |
| `docker_run_nim.sh` | Remote EC2 | Docker start script running the model with Dynamic PEFT enabled. You run this manually once at 9:00 AM. |
| `train_lora_boilerplate.py` | Remote EC2 | The Hugging Face training script. This is triggered by `ssm_trigger.py` and actually executes the fine-tune. |
