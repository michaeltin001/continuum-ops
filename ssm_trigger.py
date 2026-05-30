import boto3

def trigger_training(instance_id, dataset_s3_uri):
    ssm = boto3.client('ssm', region_name='us-east-1')
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={
            'commands': [
                f'aws s3 cp {dataset_s3_uri} /tmp/dataset.jsonl',
                'python3 /home/ubuntu/train_lora_boilerplate.py --data /tmp/dataset.jsonl --output_dir /opt/nim/loras/incident_fix'
            ]
        }
    )
    print(f"Triggered! Command ID: {response['Command']['CommandId']}")

# The exact path to the file on the remote server (/home/ubuntu/train_lora_boilerplate.py) assumes you've placed it exactly there,
# and it passes flags (--data) that your boilerplate script doesn't actually know how to read yet.