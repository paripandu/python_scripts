import boto3

# Set up AWS credentials
aws_access_key_id = '******'  # Replace with your access key
aws_secret_access_key = '*****************'  # Replace with your secret key
region_name = '*******'

def reboot_windows_servers(instance_ids):
    ec2 = boto3.client(
        'ec2',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name
    )

    # Describe instances to get their details
    response = ec2.describe_instances(InstanceIds=instance_ids)
    windows_servers = []

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            # Check for Windows OS
            if 'Windows' in instance.get('PlatformDetails', ''):
                windows_servers.append(instance['InstanceId'])

    # Print total number of Windows servers
    print(f'Total Windows servers: {len(windows_servers)}')

    # Reboot Windows servers
    if windows_servers:
        ec2.reboot_instances(InstanceIds=windows_servers)
        print(f'Rebooting Windows servers: {windows_servers}')
    else:
        print('No Windows servers to reboot.')

    return len(windows_servers)  # Return the number of Windows servers rebooted

def main():
    print("Enter instance IDs (one per line) and type 'end' when finished:")
    instance_ids = []

    while True:
        instance_id = input().strip()
        if instance_id.lower() == 'end':
            break
        instance_ids.append(instance_id)

    num_rebooted = reboot_windows_servers(instance_ids)
    print(f'Total Windows servers rebooted: {num_rebooted}')

if __name__ == "__main__":
    main()

