import boto3

def update_lambda_vpc(lambda_name, vpc_id, subnets, security_group, aws_region, aws_access_key, aws_secret_key):
    # Create a Lambda client with the provided credentials
    lambda_client = boto3.client(
        'lambda',
        region_name=aws_region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key
    )

    try:
        # Fetch the existing Lambda configuration
        response = lambda_client.get_function_configuration(FunctionName=lambda_name)

        # Create the VPC configuration
        vpc_config = {
            'SubnetIds': subnets,
            'SecurityGroupIds': [security_group]
        }

        # Update the Lambda function configuration to include VPC details
        update_response = lambda_client.update_function_configuration(
            FunctionName=lambda_name,
            VpcConfig=vpc_config
        )

        print(f"Lambda function '{lambda_name}' updated successfully with VPC: {vpc_id}, "
              f"Subnets: {', '.join(subnets)}, Security Group: {security_group}")

    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"Error: Lambda function '{lambda_name}' not found.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def main():
    # AWS Credentials and Region
    aws_region = '*******'  # Change this to your desired region
    aws_access_key = '**********'
    aws_secret_key = '*********************'

    # Take Lambda name as input
    lambda_name = input("Enter the Lambda function name: ")

    # VPC, Subnet, and Security Group details
    vpc_id = 'vpc-9898******'
    subnets = [
        'subnet-**********282c5',
        'subnet-********ae00',
        'subnet-***********2e21'
    ]
    security_group = 'sg-01*********'

    # Update Lambda with VPC configuration
    update_lambda_vpc(lambda_name, vpc_id, subnets, security_group, aws_region, aws_access_key, aws_secret_key)

if __name__ == "__main__":
    main()

