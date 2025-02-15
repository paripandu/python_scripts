import boto3

# Initialize boto3 client for CloudWatch
cloudwatch = boto3.client(
    'cloudwatch',
    aws_access_key_id='##########',
    aws_secret_access_key='###########',
    region_name='######'
)

# New SNS topic ARN
new_sns_topic_arn = "arn:aws:sns:#################"

# Function to update the SNS topic for a specific alarm
def update_alarm_sns_topic(alarm_name):
    try:
        # Get the alarm details
        response = cloudwatch.describe_alarms(AlarmNames=[alarm_name])
        alarm = response['MetricAlarms'][0]

        # If there are no alarm actions, we add the new SNS topic
        if 'AlarmActions' not in alarm or len(alarm['AlarmActions']) == 0:
            new_actions = [new_sns_topic_arn]
        else:
            # Replace all existing SNS topics with the new one
            new_actions = [new_sns_topic_arn]

        # Update the alarm with the new SNS topic
        cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            AlarmDescription=alarm.get('AlarmDescription', ''),
            ActionsEnabled=True,
            AlarmActions=new_actions,
            MetricName=alarm['MetricName'],
            Namespace=alarm['Namespace'],
            Statistic=alarm['Statistic'],
            Period=alarm['Period'],
            EvaluationPeriods=alarm['EvaluationPeriods'],
            Threshold=alarm['Threshold'],
            ComparisonOperator=alarm['ComparisonOperator'],
            Dimensions=alarm['Dimensions']
        )
        print(f'Updated SNS topic for {alarm_name}')
    except Exception as e:
        print(f"Error updating alarm {alarm_name}: {e}")

# List of alarms to update
alarms_to_update = [
    'MSP/Bhartiaxa/Non-Prod/RDS/bharti-axa-dev-postgres/FreeableMemory',
    'MSP/Bhartiaxa/Non-Prod/RDS/bharti-axa-dev-postgres/CPUUtilization',
    'MSP/Bhartiaxa/Non-Prod/EC2/Website-uat-rds/CPUUtilization',
    'MSP/Bhartiaxa/Non-Prod/RDS/edl-uat-db/i-04b727d7698dd6e0f/CPUUtilization',
    'MSP/Bhartiaxa/Non-Prod/EC2/Website-uat-rds/MemoryUtilization',
    'MSP/Bhartiaxa/Non-Prod/EC2/Website-uat-rds/DiskUtilization',
    'MSP/Bhartiaxa/Non-Prod/RDS/bharti-axa-dev-postgres/FreeStorageSpace',
    'MSP/Bhartiaxa/Non-Prod/RDS/mlife-db-dev/FreeStorageSpace',
    'MSP/Bhartiaxa/Non-Prod/RDS/digiserve/CPUUtilization',
    'MSP/Bhartiaxa/Non-Prod/RDS/digiserve/DatabaseConnections',
    'MSP/Bhartiaxa/Non-Prod/RDS/digiserve/FreeStorage',
    'MSP/Bhartiaxa/Non-Prod/RDS/digiserve/FreeableMemory',
    'MSP/Bhartiaxa/Non-Prod/RDS/edl-uat-db/i-04b727d7698dd6e0f/DiskUtilization',
    'MSP/Bhartiaxa/Non-Prod/RDS/edl-uat-db/i-04b727d7698dd6e0f/Memory Utilization',
    'MSP/Bhartiaxa/Non-Prod/RDS/bhartiaxa-edl-customer360-datalake-uat-rds/FreeableMemory',
    'MSP/Bhartiaxa/Non-Prod/RDS/bhartiaxa-edl-customer360-datalake-uat-rds/FreeStorageSpace',
    'MSP/Bhartiaxa/Non-Prod/RDS/bhartiaxa-edl-customer360-datalake-uat-rds/CPUUtilization',
    'MSP/Bhartiaxa/Non-Prod/RDS/credence-db-uat/FreeableMemory',
    'MSP/Bhartiaxa/Non-Prod/RDS/wso2-uat-psql-rds/FreeStorageSpace',
    'MSP/Bhartiaxa/Non-Prod/RDS/wso2-uat-psql-rds/CPUUtilization',
    'MSP/Bhartiaxa/Non-Prod/RDS/bharti-axa-uat-postgres/FreeStorageSpace',
    'MSP/Bhartiaxa/Non-Prod/RDS/wso2-uat-psql-rds/FreeableMemory',
    'MSP/Bhartiaxa/Non-Prod/RDS/credence-db-uat/CPUUtilization',
    'MSP/Bhartiaxa/Non-Prod/RDS/credence-db-uat/FreeStorageSpace',
    'MSP/Bhartiaxa/Non-Prod/RDS/mlife-db-dev/CPUUtilization',
    'MSP/Bhartiaxa/Non-Prod/RDS/mlife-db-dev/FreeableMemory',
    'MSP/Bhartiaxa/Non-Prod/RDS/bharti-axa-uat-postgres/FreeableMemory',
    'MSP/Bhartiaxa/Non-Prod/RDS/bharti-axa-uat-postgres/CPUUtilization',
    'MSP/Bhartiaxa/Non-Prod/RDS/digiserve-uat/CPUUtilization',
    'MSP/Bhartiaxa/Non-Prod/RDS/digiserve-uat/FreeStorageSpace',
    'MSP/Bhartiaxa/Non-Prod/RDS/digiserve-uat/DatabaseConnections',
    'MSP/Bhartiaxa/Non-Prod/RDS/digiserve-uat/FreeableMemory'
]

# Loop through alarms and update SNS topic
for alarm_name in alarms_to_update:
    update_alarm_sns_topic(alarm_name)

