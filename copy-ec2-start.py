import boto3



def start_ec2_instances(instance_ids):
    ec2 = boto3.client(
        'ec2',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_access_key_id,
        region_name=region_name
    )

    # Describe instances to get their current state
    response = ec2.describe_instances(InstanceIds=instance_ids)
    instances_to_start = []

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            state = instance['State']['Name']
            if state != 'running':
                instances_to_start.append(instance['InstanceId'])
            else:
                print(f'Skipping instance {instance["InstanceId"]} as it is already in {state} state.')

    if instances_to_start:
        ec2.start_instances(InstanceIds=instances_to_start)
        print(f'Starting instances: {instances_to_start}')
    else:
        print('No instances to start.')

    return len(instances_to_start)  # Return the number of instances started

def main():
    print("Enter instance IDs (one per line) and type 'end' when finished:")
    instance_ids = []

    while True:
        instance_id = input().strip()
        if instance_id.lower() == 'end':
            break
        instance_ids.append(instance_id)

    num_started = start_ec2_instances(instance_ids)
    print(f'Total instances started: {num_started}')

if __name__ == "__main__":
    main()

