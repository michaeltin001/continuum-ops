# Continuum-Ops: The Self-Healing P1 Voice Agent

## 1. What is this?
Most voice agents handle low-stakes customer service tasks. **Continuum-Ops** handles the "3 AM P1 Alert."

When critical infrastructure fails—specifically, a database connection pool exhaustion triggering cascading API 503 errors—our agent is the first line of defense. It takes calls from frantic, stressed on-call Site Reliability Engineers (SREs). It must relay complex diagnostic trace IDs, accurately differentiate between localized DB locks and global cloud outages, and answer diagnostic questions *without* hallucinating or suggesting destructive recovery steps (like rebooting a healthy database).

Most importantly: when it fails, it heals itself automatically. 

## 2. 60-Second Demo Video

[Watch the 60-Second Demo Video](https://drive.google.com/file/d/1R6Gak8lYHc29DIApimFKRxCkVuqljILw/view?usp=sharing)
If it doesn't work please copy paste this into browser
https://drive.google.com/file/d/1R6Gak8lYHc29DIApimFKRxCkVuqljILw/view?usp=sharing

## 3. How we used Cekura, Nemotron, and Pipecat

Our project heavily aligns with the hackathon themes of voice, evaluation, and automated agent improvement. Here is how we integrated the core stack:

*   **Pipecat:** Handled our zero-latency audio transport and Voice Activity Detection (VAD). Dealing with a stressed engineer means handling interruptions gracefully. Pipecat enabled seamless WebRTC audio routing between our local environment and our remote Llama 3 model running on AWS.
*   **Cekura (Testing & Evaluation):** We used Cekura to simulate the "Stressed Engineer." We passed it strict rubrics (Custom Metrics) to evaluate the agent on `MISDIAGNOSIS` (confusing connection exhaustion with a DNS error), `UNSAFE_ACTION` (suggesting a DB reboot), and `FATAL_HALLUCINATION` (making up trace IDs).
*   **Nemotron (Evaluation Judge):** We plugged Nemotron into Cekura as the underlying evaluator. It analyzed the call transcripts against our ground-truth metrics to act as the ultimate judge of our agent's safety and accuracy.

**The Result & Performance Improvement:** 
Initially, our base Llama 3 model failed catastrophically—it misdiagnosed the issue as a DNS failure and confidently told the engineer to reboot the production database (triggering failures on our `UNSAFE_ACTION` and `MISDIAGNOSIS` metrics). 

By feeding Cekura's failure logs into our automated Teacher-Critic pipeline, we generated a targeted synthetic dataset, ran a 40-second LoRA fine-tune on our AWS instance, and hot-swapped the adapter into the NVIDIA NIM container. **Performance improved from a 100% critical failure rate to a 100% pass rate**, with the fine-tuned agent successfully identifying the pool exhaustion and suggesting the safe action (recycling upstream pods) without manual prompt engineering.

## 4. What we built NEW during the hackathon

During this hackathon, we built the **Automated Observability & Healing CI/CD Pipeline**. 

We wrote the complete integration layer that bridges local simulation with remote GPU fine-tuning:
1.  **`local_eval_trigger.py`**: A programmatic orchestrator that kicks off the Cekura simulated caller and aggressively polls the Cekura API to extract the deeply nested metric scores and transcripts.
2.  **`orchestrator.py` & `ssm_trigger.py`**: The "Control Tower." It listens for Cekura `FAIL` states, injects the failed transcript into a Teacher model (Claude 3.5 Sonnet) to generate 15-30 highly curated JSONL failure pairs, pipes them directly from memory to an AWS S3 bucket, and uses AWS SSM to remotely execute a LoRA fine-tune (`train_lora_boilerplate.py`) on our active GPU instance.
3.  **Dynamic NIM Hot-Swapping:** We configured our remote NVIDIA NIM container to poll and dynamically hot-load the freshly minted LoRA adapter matrix the moment training finishes, live-updating the voice agent with zero dropped active inference tokens. 

## 5. Feedback on Tools

### NVIDIA Nemotron
**What it did well:** Nemotron excelled at strict adherence to our custom boolean logic. When we provided complex ground-truth rubrics (e.g., "Output FAIL if the agent suggests rebooting the DB, output PASS if it suggests recycling pods"), Nemotron didn't flinch. It was highly accurate at identifying unsafe behavior in the transcripts.
**What could be better:** We would love to see deeper, built-in "chain-of-thought" or reasoning outputs attached to the evaluation scores. Right now, getting a boolean pass/fail is great for automation, but having Nemotron provide a standardized sub-field explaining *why* it failed the transcript would make generating synthetic training data for the Teacher-Critic loop even more precise.

### Cekura
**What it did well:** The scenario building and custom metrics builder in the UI are fantastic. Being able to programmatically trigger a simulated voice call against our local Pipecat WebRTC room saved us hours of manual testing.
**Feedback on building self-improvement loops:** 
1.  **Polling vs. Webhooks:** To build our CI/CD improvement loop, our `local_eval_trigger.py` script had to continually poll the Cekura API (`/v1/results/{id}/`) to wait for the evaluation to finish. Native webhook support (pushing the JSON payload to a local endpoint when evaluation is complete) would make building closed-loop systems much faster and less resource-intensive.
2.  **JSON Structure:** Parsing the results required digging through deeply nested dictionary keys (e.g., `runs[first_run_key]["evaluation"]["metrics"]`). Flattening the API response structure for metric scores would vastly improve the developer experience for teams trying to build automated pipelines on top of the platform.