import boto3
import pandas as pd
from datetime import datetime, timedelta, timezone

# Initialize the CloudWatch client
cloudwatch = boto3.client('cloudwatch')

# Define the list of EC2 instance IDs and their names
ec2_instances = {
    'i-0cee294cb08ba1153': 'wso2-prod',
    'i-0c5e40711eed9aabf': 'prod-Instaverify2-app',
    'i-03d00f20708d50dcf': 'mlife-app-prod',
    'i-01be33057715ac0bb': 'nVEST-PROD',
    'i-0d3da8513110e2c6e': 'rule-engine-Nvest-prod',
    'i-002742c8b3b9ff331': 'prod-lwin-app-new',
    'i-04ea79470d2e2df37': 'MSmart-app-prod-new'
}

# Define the list of RDS instance IDs and their names
rds_instances = {
    'wso2-prod-psql-rds': 'wso2-prod-psql-rds',
    'prod-instaverify2-db': 'prod-instaverify2-db',
    'mlife-prod': 'mlife-prod',
    'nvest-prod': 'nvest-prod',
    'rule-engine-prod-nvest': 'rule-engine-prod-nvest',
    'prod-iwin': 'prod-iwin',
    'bharti-axa-prod-postgres': 'bharti-axa-prod-postgres',
    'online-prod': 'online-prod'
}

# Define possible namespaces and metric names for EC2
ec2_namespaces = ['CWAgent', 'cw_agent']
ec2_memory_metric_names = ['mem_used_percent', 'Memory % Committed Bytes In Use']
ec2_cpu_metric_name = 'CPUUtilization'

# Define namespace and metric names for RDS
rds_namespace = 'AWS/RDS'
rds_cpu_metric_name = 'CPUUtilization'
rds_memory_metric_name = 'FreeableMemory'

# Define the period (5 minutes in seconds)
period = 300

# Define the time range (last 5 minutes)
end_time = datetime.now(timezone.utc)  # Use timezone-aware datetime
start_time = end_time - timedelta(minutes=5)

# Function to get the maximum metric value
def get_max_metric_value(metric_name, instance_id, namespace, start_time, end_time, period):
    try:
        response = cloudwatch.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=[
                {
                    'Name': 'InstanceId' if namespace != 'AWS/RDS' else 'DBInstanceIdentifier',
                    'Value': instance_id
                },
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=period,
            Statistics=['Maximum']
        )
        
        datapoints = response['Datapoints']
        if datapoints:
            return max([dp['Maximum'] for dp in datapoints])
        else:
            return None
    except Exception as e:
        print(f"Error fetching metric {metric_name} for instance {instance_id} in namespace {namespace}: {e}")
        return None

# Function to convert bytes to gigabytes or megabytes (for RDS memory)
def format_memory(bytes_value):
    if bytes_value is None:
        return None
    if bytes_value >= 1024 ** 3:  # Convert to GB
        return f"{bytes_value / (1024 ** 3):.2f}G"
    else:  # Convert to MB
        return f"{bytes_value / (1024 ** 2):.2f}M"

# Function to format percentage values
def format_percentage(value):
    if value is None:
        return None
    return f"{round(value, 2)}%"

# Get the current date and time in the desired format
current_time = datetime.now().strftime("%d, %b & %I:%M:%S %p")

# Create lists to store results for EC2 and RDS
ec2_results = []
rds_results = []

# Fetch metrics for EC2 instances
for instance_id, instance_name in ec2_instances.items():
    print(f"Fetching metrics for EC2 instance: {instance_name} ({instance_id})")
    
    # Fetch memory utilization (try all combinations of namespaces and metric names)
    max_memory_utilization = None
    for namespace in ec2_namespaces:
        for metric_name in ec2_memory_metric_names:
            if max_memory_utilization is None:  # Stop if we find a valid value
                max_memory_utilization = get_max_metric_value(metric_name, instance_id, namespace, start_time, end_time, period)
    
    # Fetch CPU utilization (always from AWS/EC2 namespace)
    max_cpu_utilization = get_max_metric_value(ec2_cpu_metric_name, instance_id, 'AWS/EC2', start_time, end_time, period)
    
    # Append results to the EC2 list
    ec2_results.append({
        'DateTime': current_time,
        'EC2 Instance Name': f"{instance_id} ({instance_name})",
        'Max CPU (%)': format_percentage(max_cpu_utilization),
        'Max Memory (%)': format_percentage(max_memory_utilization)
    })

# Fetch metrics for RDS instances
for instance_id, instance_name in rds_instances.items():
    print(f"Fetching metrics for RDS instance: {instance_name} ({instance_id})")
    
    # Fetch CPU utilization
    max_cpu_utilization = get_max_metric_value(rds_cpu_metric_name, instance_id, rds_namespace, start_time, end_time, period)
    
    # Fetch memory utilization (in bytes) and format it
    max_memory_bytes = get_max_metric_value(rds_memory_metric_name, instance_id, rds_namespace, start_time, end_time, period)
    max_memory_formatted = format_memory(max_memory_bytes)
    
    # Append results to the RDS list
    rds_results.append({
        'DateTime': current_time,
        'RDS Instance': instance_name,
        'Max CPU (%)': format_percentage(max_cpu_utilization),
        'Freeable Memory': max_memory_formatted
    })

# Convert results to DataFrames
ec2_df = pd.DataFrame(ec2_results)
rds_df = pd.DataFrame(rds_results)

# Export the DataFrames to an Excel file with two sheets
output_file = 'infra_report.xlsx'
with pd.ExcelWriter(output_file) as writer:
    ec2_df.to_excel(writer, sheet_name='EC2 Instances', index=False)
    rds_df.to_excel(writer, sheet_name='RDS Instances', index=False)

print(f"Report exported to {output_file}")
