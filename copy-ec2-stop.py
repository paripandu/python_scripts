import boto3


def stop_ec2_instances(instance_ids):
    ec2 = boto3.client(
        'ec2',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name
    )

    # Describe instances to get their current state
    response = ec2.describe_instances(InstanceIds=instance_ids)
    instances_to_stop = []

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            state = instance['State']['Name']
            if state != 'stopped':
                instances_to_stop.append(instance['InstanceId'])
            else:
                print(f'Skipping instance {instance["InstanceId"]} as it is already in {state} state.')

    if instances_to_stop:
        ec2.stop_instances(InstanceIds=instances_to_stop)
        print(f'Stopping instances: {instances_to_stop}')
    else:
        print('No instances to stop.')

    return len(instances_to_stop)  # Return the number of instances stopped

def main():
    print("Enter instance IDs (one per line) and type 'end' when finished:")
    instance_ids = []

    while True:
        instance_id = input().strip()
        if instance_id.lower() == 'end':
            break
        instance_ids.append(instance_id)

    num_stopped = stop_ec2_instances(instance_ids)
    print(f'Total instances stopped: {num_stopped}')

if __name__ == "__main__":
    main()

