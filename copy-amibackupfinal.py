import boto3
import datetime



# Dictionary to store instance name counts
instance_name_counts = {}

# Get the current date in the format DD-MM-YYYY
date_today = datetime.datetime.now().strftime('%d-%m-%y')

def get_instance_name(instance_id):
    ec2 = boto3.resource('ec2', region_name=aws_region, aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key)
    instance = ec2.Instance(instance_id)

    base_name = None

    for tag in instance.tags:
        if tag['Key'] == 'Name':
            base_name = tag['Value']

    if base_name:
        # Increment the count for the current base name
        instance_name_counts[base_name] = instance_name_counts.get(base_name, 0) + 1
        count = instance_name_counts[base_name]

        if count > 1:
            return f"{base_name}{count - 1}"
        else:
            return base_name

def create_ami(instance_id):
    ec2_client = boto3.client('ec2', region_name=aws_region, aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key)
    instance_name = get_instance_name(instance_id)

    ami_name = f'{instance_name}-{date_today}'

    print(f"Creating AMI for instance {instance_id} ({ami_name})...")

    response = ec2_client.create_image(
        InstanceId=instance_id,
        Name=ami_name,
        Description=f"AMI Backup for instance {instance_id} ({instance_name})",
        NoReboot=True
    )

    ami_id = response['ImageId']
    print(f"AMI {ami_id} created successfully!")

    return instance_name, instance_id

def main():
    print("Enter instance IDs (one per line) and type 'end' when finished:")

    instance_ids = []
    while True:
        instance_id = input().strip()
        if instance_id.lower() == 'end':
            break
        instance_ids.append(instance_id)

    ami_count = 0

    for instance_id in instance_ids:
        instance_name, instance_id = create_ami(instance_id)
        ami_count += 1
        print(f"{instance_name} ({instance_id}) AMI has been successfully created.")

    print(f"Total {ami_count} AMIs created.")

if __name__ == "__main__":
    main()

