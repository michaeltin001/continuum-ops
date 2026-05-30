import boto3
import requests

def launch_gpu_instance():
    ec2 = boto3.client('ec2', region_name='us-east-1') # Ensure this matches your region
    ec2_resource = boto3.resource('ec2', region_name='us-east-1')

    # 1. Fetch Dynamic IP (To survive hackathon Wi-Fi)
    my_ip = requests.get('https://api.ipify.org').text
    print(f"Detected Public IP: {my_ip}")

    # 2. Get Default VPC
    vpcs = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
    vpc_id = vpcs['Vpcs'][0]['VpcId']

    # 3. Create or Fetch Security Group safely
    sg_name = 'continuum-hackathon-sg'
    try:
        sg = ec2.create_security_group(GroupName=sg_name, Description='Hackathon SG', VpcId=vpc_id)
        sg_id = sg['GroupId']
        print(f"Created fresh Security Group: {sg_id}")
    except Exception as e:
        # If it already exists, gracefully grab its ID
        sgs = ec2.describe_security_groups(GroupNames=[sg_name])
        sg_id = sgs['SecurityGroups'][0]['GroupId']
        print(f"Using existing Security Group: {sg_id}")
        
        # Wipe old IP rules so we don't conflict with our new Wi-Fi IP
        if sgs['SecurityGroups'][0]['IpPermissions']:
            ec2.revoke_security_group_ingress(GroupId=sg_id, IpPermissions=sgs['SecurityGroups'][0]['IpPermissions'])
            print("Flushed outdated network rules.")

    # 4. Safely apply current live IP rules (Executed 100% of the time, keeping Port 443)
    print(f"Authorizing access for your current Wi-Fi IP ({my_ip})...")
    ec2.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': f'{my_ip}/32'}]},
            {'IpProtocol': 'tcp', 'FromPort': 8000, 'ToPort': 8000, 'IpRanges': [{'CidrIp': f'{my_ip}/32'}]},
            {'IpProtocol': 'tcp', 'FromPort': 443, 'ToPort': 443, 'IpRanges': [{'CidrIp': f'{my_ip}/32'}]}
        ]
    )
    print("Network permissions locked in!")

    # 5. Launch the ON-DEMAND Instance
    print("Launching On-Demand Instance...")
    instances = ec2_resource.create_instances(
        ImageId='ami-001a56577de554264', # <--- UPDATE THIS STRING
        MinCount=1,
        MaxCount=1,
        InstanceType='g5.2xlarge',
        KeyName='continuum-key',
        SecurityGroupIds=[sg_id],
        IamInstanceProfile={'Name': 'ContinuumAgentRole'},
        BlockDeviceMappings=[
            {
                'DeviceName': '/dev/sda1',  # Standard root device name for Ubuntu AMIs
                'Ebs': {
                    'VolumeSize': 150,       # Size in GB
                    'VolumeType': 'gp3',     # Next-gen SSD (Faster and cheaper than gp2)
                    'DeleteOnTermination': True  # Automatically wipes storage when you terminate the instance
                }
            }
        ]
    )
    print(f"Success! Instance ID: {instances[0].id}")

if __name__ == "__main__":
    launch_gpu_instance()