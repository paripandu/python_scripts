import boto3

# Set AWS credentials
aws_region = '******'
aws_access_key = '#############'
aws_secret_key = '###############'

# AWS SQS client
sqs = boto3.client(
    'sqs',
    region_name=aws_region,
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key
)

def get_queue_url(queue_name):
    """Retrieve the queue URL if it exists."""
    try:
        response = sqs.get_queue_url(QueueName=queue_name)
        return response['QueueUrl']
    except sqs.exceptions.QueueDoesNotExist:
        return None

def create_sqs_queue(queue_name, dlq_arn=None):
    """Create an SQS queue with the specified attributes."""
    is_dlq = "-DLQ.fifo" in queue_name
    attributes = {
        "FifoQueue": "true",
        "MessageRetentionPeriod": "1209600",  # 14 days in seconds
        "ContentBasedDeduplication": "true",
    }
    tags = {
        "Project": "AOL",
        "Name": queue_name,
        "Environment": "Production",
        "Managed-By": "TTN"
    }

    # Add DLQ settings if applicable
    if not is_dlq and dlq_arn:
        attributes["RedrivePolicy"] = f'{{"deadLetterTargetArn":"{dlq_arn}","maxReceiveCount":"5"}}'

    # Check if the queue already exists
    existing_queue_url = get_queue_url(queue_name)
    if existing_queue_url:
        print(f"Queue already exists: {queue_name}")
        return existing_queue_url

    # Create the queue
    response = sqs.create_queue(
        QueueName=queue_name,
        Attributes=attributes,
        tags=tags
    )
    print(f"Queue created: {queue_name}")
    print(f"Queue URL: {response['QueueUrl']}")
    if dlq_arn:
        print(f"Linked DLQ ARN: {dlq_arn}")
    return response['QueueUrl']

def main():
    # Get queue name from user input
    first_queue_name = input("Enter the name of the first queue (DLQ): ")
    second_queue_name = input("Enter the name of the second queue (regular queue): ")

    # Create the first queue (DLQ)
    dlq_url = create_sqs_queue(first_queue_name)

    # Fetch the ARN of the first queue to use as DLQ for the second queue
    first_queue_arn = sqs.get_queue_attributes(
        QueueUrl=dlq_url,
        AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]

    # Create the second queue (regular queue with DLQ)
    create_sqs_queue(second_queue_name, dlq_arn=first_queue_arn)

if __name__ == "__main__":
    main()

