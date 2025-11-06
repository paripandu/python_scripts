import boto3
import pandas as pd
import re
from datetime import datetime
import logging
import argparse
import sys
from botocore.exceptions import ClientError, BotoCoreError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CloudWatchAlarmReport:
    def __init__(self, profile_name=None, region_name='ap-south-1'):
        """
        Initialize AWS clients
        """
        try:
            if profile_name:
                session = boto3.Session(profile_name=profile_name)
                self.cloudwatch = session.client('cloudwatch', region_name=region_name)
                self.ec2 = session.client('ec2', region_name=region_name)
                self.rds = session.client('rds', region_name=region_name)
                self.elasticache = session.client('elasticache', region_name=region_name)
                self.elbv2 = session.client('elbv2', region_name=region_name)
                self.apigateway = session.client('apigateway', region_name=region_name)
                self.ecs = session.client('ecs', region_name=region_name)
                self.lambda_client = session.client('lambda', region_name=region_name)
                logger.info(f"Using AWS profile: {profile_name} in region: {region_name}")
            else:
                self.cloudwatch = boto3.client('cloudwatch', region_name=region_name)
                self.ec2 = boto3.client('ec2', region_name=region_name)
                self.rds = boto3.client('rds', region_name=region_name)
                self.elasticache = boto3.client('elasticache', region_name=region_name)
                self.elbv2 = boto3.client('elbv2', region_name=region_name)
                self.apigateway = boto3.client('apigateway', region_name=region_name)
                self.ecs = boto3.client('ecs', region_name=region_name)
                self.lambda_client = boto3.client('lambda', region_name=region_name)
                logger.info(f"Using default AWS credentials in region: {region_name}")
                
            # Test connection
            self.cloudwatch.describe_alarms(MaxRecords=1)
            logger.info("Successfully connected to AWS CloudWatch")
            
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {e}")
            raise

    def get_all_cloudwatch_alarms(self):
        """
        Fetch all CloudWatch alarms
        """
        alarms = []
        paginator = self.cloudwatch.get_paginator('describe_alarms')
        
        try:
            for page in paginator.paginate():
                alarms.extend(page['MetricAlarms'])
            logger.info(f"Total alarms fetched: {len(alarms)}")
            return alarms
        except Exception as e:
            logger.error(f"Error fetching alarms: {e}")
            return []

    def get_resource_type_from_namespace(self, namespace):
        """
        Map CloudWatch namespace to resource type
        """
        namespace_mapping = {
            'AWS/EC2': 'EC2',
            'AWS/RDS': 'RDS',
            'AWS/ElastiCache': 'ElastiCache',
            'AWS/ApplicationELB': 'ALB',
            'AWS/NetworkELB': 'NLB',
            'AWS/ELB': 'ELB',
            'AWS/ApiGateway': 'API Gateway',
            'AWS/ECS': 'ECS',
            'AWS/Lambda': 'Lambda',
            'AWS/S3': 'S3',
            'AWS/DynamoDB': 'DynamoDB',
            'AWS/SQS': 'SQS',
            'AWS/SNS': 'SNS',
            'AWS/CloudFront': 'CloudFront',
            'AWS/Route53': 'Route53',
            'AWS/Redshift': 'Redshift',
            'AWS/EBS': 'EBS',
            'AWS/EFS': 'EFS',
            'AWS/StorageGateway': 'Storage Gateway'
        }
        return namespace_mapping.get(namespace, 'Unknown')

    def get_resource_info_from_dimensions(self, dimensions, resource_type):
        """
        Extract resource information from alarm dimensions
        """
        resource_id = None
        resource_name = None
        
        if not dimensions:
            return resource_id, resource_name
            
        dimension_map = {}
        for dim in dimensions:
            dimension_map[dim['Name']] = dim['Value']
        
        # Map dimensions based on resource type
        if resource_type == 'EC2':
            resource_id = dimension_map.get('InstanceId')
        elif resource_type == 'RDS':
            resource_id = dimension_map.get('DBInstanceIdentifier')
            if not resource_id:
                resource_id = dimension_map.get('DBClusterIdentifier')
        elif resource_type == 'ElastiCache':
            resource_id = dimension_map.get('CacheClusterId')
        elif resource_type in ['ALB', 'NLB', 'ELB']:
            resource_id = dimension_map.get('LoadBalancer')
            if not resource_id:
                resource_id = dimension_map.get('LoadBalancerName')
        elif resource_type == 'API Gateway':
            resource_id = dimension_map.get('ApiName')
            if not resource_id:
                resource_id = dimension_map.get('ApiId')
        elif resource_type == 'ECS':
            resource_id = dimension_map.get('ClusterName')
            service_name = dimension_map.get('ServiceName')
            if service_name:
                resource_id = f"{resource_id}/{service_name}"
        elif resource_type == 'Lambda':
            resource_id = dimension_map.get('FunctionName')
        elif resource_type == 'S3':
            resource_id = dimension_map.get('BucketName')
        elif resource_type == 'DynamoDB':
            resource_id = dimension_map.get('TableName')
        
        resource_name = resource_id
        return resource_id, resource_name

    def get_resource_name_from_aws_api(self, resource_type, resource_id):
        """
        Get resource name from AWS API calls
        """
        try:
            if resource_type == 'EC2' and resource_id.startswith('i-'):
                response = self.ec2.describe_instances(InstanceIds=[resource_id])
                for reservation in response['Reservations']:
                    for instance in reservation['Instances']:
                        for tag in instance.get('Tags', []):
                            if tag['Key'] == 'Name':
                                return tag['Value']
            
            elif resource_type == 'RDS':
                try:
                    response = self.rds.describe_db_instances(DBInstanceIdentifier=resource_id)
                    for db_instance in response['DBInstances']:
                        return db_instance.get('DBInstanceIdentifier', resource_id)
                except ClientError:
                    # Try DB clusters
                    response = self.rds.describe_db_clusters(DBClusterIdentifier=resource_id)
                    for db_cluster in response['DBClusters']:
                        return db_cluster.get('DBClusterIdentifier', resource_id)
            
            elif resource_type == 'ALB':
                response = self.elbv2.describe_load_balancers(LoadBalancerArns=[resource_id])
                for lb in response['LoadBalancers']:
                    return lb.get('LoadBalancerName', resource_id)
            
            elif resource_type == 'API Gateway':
                response = self.apigateway.get_rest_api(restApiId=resource_id)
                return response.get('name', resource_id)
            
            elif resource_type == 'Lambda':
                response = self.lambda_client.get_function(FunctionName=resource_id)
                return response['Configuration']['FunctionName']
                
        except (ClientError, BotoCoreError) as e:
            logger.debug(f"Could not get resource name for {resource_type}/{resource_id}: {e}")
        
        return resource_id

    def extract_resource_info_comprehensive(self, alarm):
        """
        Comprehensive resource information extraction using multiple methods
        """
        alarm_name = alarm['AlarmName']
        namespace = alarm.get('Namespace', '')
        metric_name = alarm.get('MetricName', '')
        dimensions = alarm.get('Dimensions', [])
        
        # Method 1: Get resource type from namespace (most reliable)
        resource_type = self.get_resource_type_from_namespace(namespace)
        
        # Method 2: Get resource info from dimensions
        resource_id, resource_name = self.get_resource_info_from_dimensions(dimensions, resource_type)
        
        # Method 3: If no resource ID from dimensions, try alarm name patterns
        if not resource_id:
            resource_id, resource_name = self.extract_from_alarm_name(alarm_name, resource_type)
        
        # Method 4: Enhance resource name using AWS APIs
        if resource_id and resource_id != 'Unknown':
            enhanced_name = self.get_resource_name_from_aws_api(resource_type, resource_id)
            if enhanced_name and enhanced_name != resource_id:
                resource_name = enhanced_name
        
        # Final fallback to alarm name patterns if still no resource info
        if resource_type == 'Unknown' or not resource_id:
            resource_type, resource_id, resource_name = self.fallback_alarm_name_parsing(alarm_name)
        
        return resource_type, resource_id, resource_name, metric_name

    def extract_from_alarm_name(self, alarm_name, resource_type):
        """
        Extract resource information from alarm name as fallback
        """
        resource_id = None
        resource_name = None
        
        patterns = {
            'EC2': [
                r'/(i-[a-f0-9]+)/',
                r'InstanceId=?(i-[a-f0-9]+)',
                r'InstanceId(i-[a-f0-9]+)',
            ],
            'RDS': [
                r'/([a-zA-Z0-9-]+-rds-?[a-zA-Z0-9-]*)/',
                r'/([a-zA-Z0-9-]+-db-?[a-zA-Z0-9-]*)/',
                r'RDS/([^/]+)/',
            ],
            'ALB': [
                r'/(app/[^/]+)/',
                r'/(arn:aws:elasticloadbalancing:[^/]+/[^/]+/[^/]+)/',
            ],
            'API Gateway': [
                r'API/([^/]+)/([^/]+)',
                r'/([a-zA-Z0-9-]+-api-?[a-zA-Z0-9-]*)/',
            ],
            'ECS': [
                r'ECS/([^/]+)/([^/]+)',
                r'/([a-zA-Z0-9-]+-cluster-?[a-zA-Z0-9-]*)/',
            ]
        }
        
        for res_type, type_patterns in patterns.items():
            if resource_type != 'Unknown' and resource_type != res_type:
                continue
                
            for pattern in type_patterns:
                match = re.search(pattern, alarm_name, re.IGNORECASE)
                if match:
                    resource_id = match.group(1)
                    resource_name = resource_id
                    break
            if resource_id:
                break
        
        return resource_id, resource_name

    def fallback_alarm_name_parsing(self, alarm_name):
        """
        Final fallback to alarm name pattern matching
        """
        resource_type = "Unknown"
        resource_id = "Unknown"
        resource_name = "Unknown"
        
        # Common patterns in your alarm names
        patterns = [
            (r'MSP/[^/]+/[^/]+/EC2/([^/]+)/([^/]+)', 'EC2'),
            (r'MSP/[^/]+/[^/]+/TG/([^/]+)/([^/]+)', 'Target Group'),
            (r'MSP/[^/]+-?Prod?/RDS/([^/]+)/([^/]+)', 'RDS'),
            (r'AWS/MSP/[^/]+/API/([^/]+)/([^/]+)', 'API Gateway'),
            (r'MSP/[^/]+/[^/]+/ECS/([^/]+)/([^/]+)/([^/]+)', 'ECS'),
            (r'AWS/EC2/([^/]+)/([^/]+)', 'EC2'),
            (r'AWS/RDS/([^/]+)/([^/]+)', 'RDS'),
        ]
        
        for pattern, res_type in patterns:
            match = re.search(pattern, alarm_name, re.IGNORECASE)
            if match:
                resource_type = res_type
                groups = match.groups()
                resource_id = groups[0] if groups else "Unknown"
                resource_name = resource_id
                break
        
        return resource_type, resource_id, resource_name

    def categorize_metric(self, metric_name, resource_type):
        """
        Categorize metrics based on metric name and resource type
        """
        if not metric_name or metric_name == "Unknown":
            return "Other"
            
        metric_name_lower = metric_name.lower()
        
        # CPU related metrics
        cpu_indicators = ['cpu', 'processor', 'cpucredit']
        if any(indicator in metric_name_lower for indicator in cpu_indicators):
            return 'CPU'
        
        # Memory related metrics
        memory_indicators = ['memory', 'mem', 'ram', 'freeable', 'swap']
        if any(indicator in metric_name_lower for indicator in memory_indicators):
            return 'Memory'
        
        # Disk/Storage related metrics
        disk_indicators = ['disk', 'storage', 'volume', 'ebs', 'space', 'bytes']
        if any(indicator in metric_name_lower for indicator in disk_indicators):
            return 'Disk'
        
        # Network related metrics
        network_indicators = ['network', 'bandwidth', 'packets', 'throughput']
        if any(indicator in metric_name_lower for indicator in network_indicators):
            return 'Network'
        
        # Status/Health related metrics
        status_indicators = ['status', 'health', 'check', 'healthy', 'unhealthy', 'state']
        if any(indicator in metric_name_lower for indicator in status_indicators):
            return 'Status'
        
        # Performance related metrics
        performance_indicators = ['latency', 'response', 'duration', 'time', 'delay']
        if any(indicator in metric_name_lower for indicator in performance_indicators):
            return 'Performance'
        
        # Error related metrics
        error_indicators = ['error', '4xx', '5xx', 'failure', 'throttle', 'timeout']
        if any(indicator in metric_name_lower for indicator in error_indicators):
            return 'Errors'
        
        # Capacity/Count related metrics
        count_indicators = ['count', 'connection', 'invocation', 'request', 'item']
        if any(indicator in metric_name_lower for indicator in count_indicators):
            return 'Capacity'
        
        return 'Other'

    def process_alarms(self, alarms):
        """
        Process alarms using comprehensive resource detection
        """
        processed_data = []
        
        logger.info("Processing alarms with comprehensive resource detection...")
        
        for alarm in alarms:
            alarm_name = alarm['AlarmName']
            alarm_state = alarm['StateValue']
            namespace = alarm.get('Namespace', '')
            
            # Comprehensive resource information extraction
            resource_type, resource_id, resource_name, metric_name = self.extract_resource_info_comprehensive(alarm)
            
            # Categorize the metric
            metric_category = self.categorize_metric(metric_name, resource_type)
            
            processed_data.append({
                'resource_type': resource_type,
                'resource_id': resource_id,
                'resource_name': resource_name,
                'alarm_name': alarm_name,
                'metric_name': metric_name,
                'metric_category': metric_category,
                'alarm_state': alarm_state,
                'namespace': namespace
            })
        
        return processed_data

    def create_excel_report(self, processed_data, output_file='cloudwatch_alarms_report.xlsx'):
        """
        Create Excel report with separate sheets per resource type and one for unknown resources
        """
        try:
            # Create DataFrame
            df = pd.DataFrame(processed_data)
            
            if df.empty:
                logger.warning("No data to write to Excel")
                return False
            
            # Sort by resource type and name
            df = df.sort_values(['resource_type', 'resource_name', 'metric_category', 'metric_name'])
            
            # Create Excel writer
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                
                # Separate data by resource type
                resource_types = df['resource_type'].unique()
                
                for resource_type in resource_types:
                    if resource_type == 'Unknown':
                        continue  # Handle Unknown separately
                    
                    resource_data = df[df['resource_type'] == resource_type]
                    
                    # Create formatted data for this resource type
                    formatted_data = self._format_resource_sheet_data(resource_data)
                    formatted_df = pd.DataFrame(formatted_data)
                    
                    # Use shortened sheet name (Excel limit is 31 characters)
                    sheet_name = resource_type[:31]
                    formatted_df.to_excel(writer, sheet_name=sheet_name, index=False)
                    logger.info(f"Created sheet for {resource_type} with {len(resource_data)} alarms")
                
                # Create sheet for Unknown resources
                unknown_data = df[df['resource_type'] == 'Unknown']
                if not unknown_data.empty:
                    formatted_unknown = self._format_resource_sheet_data(unknown_data)
                    formatted_unknown_df = pd.DataFrame(formatted_unknown)
                    formatted_unknown_df.to_excel(writer, sheet_name='Unknown_Resources', index=False)
                    logger.info(f"Created sheet for Unknown resources with {len(unknown_data)} alarms")
                else:
                    # Create empty sheet for consistency
                    empty_df = pd.DataFrame({'Message': ['No unknown resources found']})
                    empty_df.to_excel(writer, sheet_name='Unknown_Resources', index=False)
            
            logger.info(f"Excel report generated: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating Excel report: {e}")
            return False

    def _format_resource_sheet_data(self, resource_data):
        """
        Format data for resource-specific sheets
        """
        formatted_data = []
        
        # Group by resource name
        for resource_name, group in resource_data.groupby('resource_name'):
            # Add resource header
            formatted_data.append({
                'Resource Name': resource_name,
                'Alarm Name': '=== RESOURCE ===',
                'Metric Name': '',
                'Metric Category': '',
                'Alarm State': '',
                'Namespace': ''
            })
            
            # Add alarms for this resource
            for _, row in group.iterrows():
                formatted_data.append({
                    'Resource Name': '',
                    'Alarm Name': row['alarm_name'],
                    'Metric Name': row['metric_name'],
                    'Metric Category': row['metric_category'],
                    'Alarm State': row['alarm_state'],
                    'Namespace': row['namespace']
                })
            
            # Add empty row for separation
            formatted_data.append({
                'Resource Name': '',
                'Alarm Name': '',
                'Metric Name': '',
                'Metric Category': '',
                'Alarm State': '',
                'Namespace': ''
            })
        
        return formatted_data

    def generate_report(self, output_file=None):
        """
        Main method to generate the complete report
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f'cloudwatch_alarms_report_{timestamp}.xlsx'
        
        logger.info("Fetching CloudWatch alarms...")
        alarms = self.get_all_cloudwatch_alarms()
        
        if not alarms:
            logger.error("No alarms found or error fetching alarms")
            return False
        
        logger.info("Processing alarm data with comprehensive detection...")
        processed_data = self.process_alarms(alarms)
        
        logger.info("Creating Excel report with resource-wise sheets...")
        success = self.create_excel_report(processed_data, output_file)
        
        if success:
            logger.info(f"Report successfully generated: {output_file}")
            logger.info(f"Total alarms processed: {len(processed_data)}")
            
            # Print summary to console
            self.print_resource_summary(processed_data)
            
        return success

    def print_resource_summary(self, processed_data):
        """
        Print resource-wise summary to console
        """
        df = pd.DataFrame(processed_data)
        
        print(f"\n{'='*80}")
        print(f"CLOUDWATCH ALARMS REPORT - RESOURCE WISE")
        print(f"{'='*80}")
        print(f"Total Alarms: {len(processed_data)}")
        print(f"{'='*80}")
        
        # Resource Type Breakdown
        print("\nRESOURCE TYPE BREAKDOWN (Sheets in Excel):")
        print("-" * 50)
        resource_counts = df['resource_type'].value_counts()
        
        for resource_type, count in resource_counts.items():
            unique_resources = df[df['resource_type'] == resource_type]['resource_name'].nunique()
            print(f"  {resource_type:<20} {count:>4} alarms ({unique_resources:>3} resources)")
        
        print(f"\nTotal Sheets: {len(resource_counts)}")
        print(f"{'='*80}")

def setup_argparse():
    """
    Set up command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Generate CloudWatch Alarms Report with Resource-wise Sheets',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Use default AWS credentials
  python cloudwatch_alarm_report.py
  
  # Use specific AWS profile
  python cloudwatch_alarm_report.py --profile my-profile
  
  # Use specific region with verbose logging
  python cloudwatch_alarm_report.py --region us-east-1 --verbose
  
  # Custom output file with profile
  python cloudwatch_alarm_report.py --profile production --output resource_wise_report.xlsx
        '''
    )
    
    parser.add_argument(
        '--profile',
        type=str,
        help='AWS profile name to use (from ~/.aws/credentials)'
    )
    
    parser.add_argument(
        '--region',
        type=str,
        default='ap-south-1',
        help='AWS region name (default: ap-south-1)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Output Excel file name'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()

def main():
    """
    Main execution function
    """
    args = setup_argparse()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize the report generator
        report_generator = CloudWatchAlarmReport(
            profile_name=args.profile,
            region_name=args.region
        )
        
        # Generate the report
        success = report_generator.generate_report(args.output)
        
        if success:
            print("\n✅ Resource-wise report generation completed successfully!")
            print("📊 Each resource type has its own sheet in the Excel file")
            print("❓ Unknown resources are grouped in 'Unknown_Resources' sheet")
            sys.exit(0)
        else:
            print("\n❌ Report generation failed!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
