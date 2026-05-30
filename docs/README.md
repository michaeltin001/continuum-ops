# **Continuum-Ops**

## Overview

Most voice agents handle low-stakes customer service. Continuum-Ops handles the "3 AM P1 Alert." When a database connection exhaustion triggers a cascading API failure, the agent calls the on-call engineer. It must relay complex trace IDs, accurately differentiate between a localized DB lock and a global cloud outage, and answer diagnostic questions without suggesting destructive recovery steps.

It hits every theme perfectly. It’s high-stakes, uses Pipecat for zero-latency interruption (essential for a frantic engineer), relies on Nemotron/Cekura for rigorous evaluation of technical logs, and uses an automated fine-tuning loop on 15–30 highly curated synthetic failure pairs to stop critical misdiagnoses cold.

## Architecture

- The Voice/Network Layer (Deploy at Scale): Daily’s WebRTC and Pipecat. This handles audio transport and Voice Activity Detection (VAD). We utilize Deepgram (STT) and Cartesia (TTS) as the gold standards for ultra-low latency audio processing.
- The Brain (Build & Customize): Llama 3 hosted on AWS EC2 instances, accelerated by NVIDIA NIM for ultra-low latency token generation.
- The Evaluator (Simulate & Evaluate): Cekura’s testing harness. You will use Cekura to simulate a stressed engineer. You will plug Nemotron in as the judge model to evaluate factual accuracy against a synthetic "P1 Incident Log."
- The Observability Loop: Integrated Logfire or Langsmith to trace the voice-to-text-to-agent chain and pinpoint exactly where the feedback loop requires intervention.
- The Harness (Auto-Improve): A Teacher-Critic pipeline (using Claude). When Nemotron flags a misdiagnosis or safety violation, the Teacher generates 15–30 targeted training pairs. These are piped via Memory-to-S3-to-SSM to trigger a LoRA fine-tune on an AWS On-Demand Instance, which is then hot-swapped into the running NVIDIA NIM endpoint.

## Setup

```
# Core tools, Python speed, and Tailscale for network resilience
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential curl git docker.io python3-pip
curl -fsSL https://tailscale.com/install.sh | sh
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
uv venv && source .venv/bin/activate

# Install Pipecat with specific provider extras and observability
uv pip install "pipecat-ai[deepgram,cartesia,openai]" daily-python boto3 anthropic python-dotenv requests logfire langsmith python-dotenv
```

```
# 1. Log into NVIDIA's registry interactively
# When it asks for Username, type exactly: $oauthtoken
# When it asks for Password, paste your nvapi- key (it will be invisible)
docker login nvcr.io

# 2. Pull the Llama 3.1 8B Instruct model
docker pull nvcr.io/nim/meta/llama-3.1-8b-instruct:latest

# 3. Create the directory where our LoRA fine-tunes will live
sudo mkdir -p /opt/nim/loras
sudo chmod 777 /opt/nim/loras
```

## Helpful Commands

Activate the virtual environment
```
source .venv/bin/activate
```

Deactivate the virtual environment
```
deactivate
```

Fetch current public IP
```
curl https://api.ipify.org
```

Update IP
```
python3 update_ip.py
```

SSH into AWS EC2 instance
```
ssh -i continuum-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

SSH into AWS EC2 instance (VS Code)
```
ssh -i /home/michael/Desktop/continuum-ops/continuum-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

See all docker images
```
docker images
```

See the `/opt/nim/loras` directory
```
ls -ld /opt/nim/loras
```

Copy files to AWS EC2 instance
```
scp -i continuum-key.pem docker_run_nim.sh train_lora_boilerplate.py ubuntu@YOUR_EC2_PUBLIC_IP:/home/ubuntu/
```

Stop AWS EC2 instances
```
aws ec2 stop-instances --instance-ids i-062c2033da45c2a80
```

Terminate AWS EC2 instances
```
aws ec2 terminate-instances --instance-ids i-062c2033da45c2a80 --force
```

Tail NIM logs
```
terminator -e "ssh -i /path/to/continuum-key.pem ubuntu@YOUR_EC2_PUBLIC_IP 'docker logs -f \$(docker ps -q --filter ancestor=nvcr.io/nim/meta/llama-3.1-8b-instruct:latest)'"
```

Hard reset environment
```
terminator -e "python3 /path/to/your/project/reset_environment.py"
```