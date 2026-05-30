import os
import boto3
from dotenv import load_dotenv
from rich.console import Console

load_dotenv(override=True)
console = Console()

def reset_demo_state():
    console.print("[bold yellow]🧹 Initializing complete environment reset...[/]")

    # Clear the remote LoRA adapter files so NVIDIA NIM reverts to the base model
    instance_id = os.getenv("EC2_INSTANCE_ID")
    region = os.getenv("AWS_REGION", "us-east-1")
    ssm = boto3.client('ssm', region_name=region)
    
    # We remove the files inside the folder so NIM registers the deletion
    commands = [
        "sudo rm -rf /opt/nim/loras/incident_fix/*",
        "echo 'Remote adapter purged.'"
    ]
    
    try:
        ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={'commands': commands}
        )
        console.print("[bold green][AWS SSM] Remote LoRA directory purged. NIM falling back to base model...[/]")
    except Exception as e:
        console.print(f"[red]Failed to clear remote instance weights: {e}[/]")

    console.print("[bold bright_green]✨ DEMO ENVIRONMENT RESET COMPLETE. READY FOR THE NEXT JUDGE. ✨[/]")

if __name__ == "__main__":
    reset_demo_state()