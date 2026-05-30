import boto3
import requests

def update_firewall():
    ec2 = boto3.client('ec2', region_name='us-east-1')
    my_ip = requests.get('https://api.ipify.org').text
    sg_name = 'continuum-hackathon-sg'

    # Find your group
    sgs = ec2.describe_security_groups(GroupNames=[sg_name])
    sg_id = sgs['SecurityGroups'][0]['GroupId']
    
    # Wipe the old rules
    if sgs['SecurityGroups'][0]['IpPermissions']:
        ec2.revoke_security_group_ingress(GroupId=sg_id, IpPermissions=sgs['SecurityGroups'][0]['IpPermissions'])

    # Apply your new Wi-Fi IP
    ec2.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': f'{my_ip}/32'}]},
            {'IpProtocol': 'tcp', 'FromPort': 8000, 'ToPort': 8000, 'IpRanges': [{'CidrIp': f'{my_ip}/32'}]},
            {'IpProtocol': 'tcp', 'FromPort': 443, 'ToPort': 443, 'IpRanges': [{'CidrIp': f'{my_ip}/32'}]}
        ]
    )
    print(f"Firewall updated! You can now SSH in from IP: {my_ip}")

if __name__ == "__main__":
    update_firewall()