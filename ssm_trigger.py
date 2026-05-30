import boto3
import os

def trigger_training(instance_id, dataset_s3_uri):
    """
    Addressed Phase 3 Objective: "trigger the AWS SSM command to start the LoRA fine-tune."
    
    This function is invoked by orchestrator.py. It connects to AWS Systems Manager (SSM) 
    to securely execute terminal commands on the remote EC2 GPU instance without needing 
    an active SSH session or exposed ports.
    """
    
    # -------------------------------------------------------------------------
    # SSM CLIENT INITIALIZATION
    # Addressed Project Summary: "The AWS Boto3 utility module imported by the 
    # orchestrator to fire the remote execution command across the internet."
    # -------------------------------------------------------------------------
    # Fetches the region dynamically from the .env file, defaulting to us-east-1
    region = os.getenv("AWS_REGION", "us-east-1")
    ssm = boto3.client('ssm', region_name=region)
    
    # -------------------------------------------------------------------------
    # REMOTE COMMAND DEFINITION
    # Addressed Phase 3 Pipeline Steps 3 & 4:
    # - "Boto3 invokes ssm_trigger.py"
    # - "Remote instance trains and dumps weights to /opt/nim/loras/incident_fix"
    # 
    # Addressed argparse logic from train_lora_boilerplate.py:
    # Passes the explicit --data and --output_dir flags. The EC2 instance has the 
    # IAM profile 'ContinuumAgentRole' (from launch_infrastructure.py), granting 
    # it permission to run 'aws s3 cp' natively.
    # -------------------------------------------------------------------------
    commands = [
        f'aws s3 cp {dataset_s3_uri} /tmp/dataset.jsonl',
        # CHANGED THIS LINE: We explicitly call the .venv python so it finds bitsandbytes!
        '/home/ubuntu/.venv/bin/python3 /home/ubuntu/train_lora_boilerplate.py --data /tmp/dataset.jsonl --output_dir /opt/nim/loras/incident_fix'
    ]
    
    print(f"Sending SSM command to remote instance {instance_id}...")
    
    try:
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={
                'commands': commands
            },
            # Allow enough time for the fast LoRA to finish before SSM times out
            TimeoutSeconds=600 
        )
        
        command_id = response['Command']['CommandId']
        print(f"Success! Triggered remote fine-tuning pipeline. Command ID: {command_id}")
        return command_id
        
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to trigger SSM execution. Trace: {e}")
        raise e

# The exact path to the file on the remote server (/home/ubuntu/train_lora_boilerplate.py) assumes you've placed it exactly there,