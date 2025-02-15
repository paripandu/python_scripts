import boto3

# List of dictionaries containing cluster and node group information
node_groups_to_upgrade = [
    {
        'aws_account_id': '#######',  # Replace with Account ID
        'role_name': '#########',       # Replace with Role Name
        'cluster_name': '#########',
        'nodegroup_name': '########',
        'min_size': 0,
        'max_size': 1,
        'desired_size': 0
    }
    # Add more entries as needed
]

aws_region = 'ap-south-1'  # Replace with the appropriate region

# Upgrade the specified node groups in different AWS accounts
def upgrade_node_groups():
    for node_group in node_groups_to_upgrade:
        aws_account_id = node_group['aws_account_id']
        role_name = node_group['role_name']
        cluster_name = node_group['cluster_name']
        nodegroup_name = node_group['nodegroup_name']
        min_size = node_group['min_size']
        max_size = node_group['max_size']
        desired_size = node_group['desired_size']

        try:
            sts_client = boto3.client('sts')
            assumed_role = sts_client.assume_role(
                RoleArn=f'arn:aws:iam::{aws_account_id}:role/{role_name}',
                RoleSessionName='AssumedRoleSession'
            )

            assumed_credentials = assumed_role['Credentials']
            eks_client_assumed = boto3.client(
                'eks',
                region_name=aws_region,
                aws_access_key_id=assumed_credentials['AccessKeyId'],
                aws_secret_access_key=assumed_credentials['SecretAccessKey'],
                aws_session_token=assumed_credentials['SessionToken']
            )

            response = eks_client_assumed.update_nodegroup_config(
                clusterName=cluster_name,
                nodegroupName=nodegroup_name,
                scalingConfig={
                    'minSize': min_size,
                    'maxSize': max_size,
                    'desiredSize': desired_size
                }
            )
            print(f"Node group '{nodegroup_name}' in cluster '{cluster_name}' is being upgraded in AWS account {aws_account_id}.")
        except Exception as e:
            print(f"Error upgrading node group '{nodegroup_name}' in cluster '{cluster_name}': {str(e)}")

if __name__ == '__main__':
    upgrade_node_groups()
