import boto3
import pandas as pd
import re
from datetime import datetime
import logging
import argparse
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CloudWatchAlarmReport:
    def __init__(self, profile_name=None, region_name='ap-south-1'):
        """
        Initialize CloudWatch client
        """
        try:
            if profile_name:
                session = boto3.Session(profile_name=profile_name)
                self.cloudwatch = session.client('cloudwatch', region_name=region_name)
                self.ec2 = session.client('ec2', region_name=region_name)
                logger.info(f"Using AWS profile: {profile_name} in region: {region_name}")
            else:
                self.cloudwatch = boto3.client('cloudwatch', region_name=region_name)
                self.ec2 = boto3.client('ec2', region_name=region_name)
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

    def extract_instance_info(self, alarm_name, namespace, metric_name, dimensions):
        """
        Extract instance ID and name from alarm name and dimensions
        """
        instance_id = None
        instance_name = None
        
        # Common patterns in alarm names for instance ID
        instance_id_patterns = [
            r'.*/(i-[a-f0-9]+)(?:/|$).*',
            r'InstanceId=?(i-[a-f0-9]+)',
            r'.*\s(i-[a-f0-9]+)\s.*',
            r'.*InstanceId(i-[a-f0-9]+).*',
        ]
        
        # Try to extract instance ID from alarm name
        for pattern in instance_id_patterns:
            match = re.search(pattern, alarm_name, re.IGNORECASE)
            if match:
                instance_id = match.group(1)
                break
        
        # If no instance ID found in alarm name, check dimensions
        if not instance_id and dimensions:
            for dimension in dimensions:
                if dimension['Name'] == 'InstanceId':
                    instance_id = dimension['Value']
                    break
                elif dimension['Name'] == 'InstanceId,':
                    # Handle malformed dimension names
                    instance_id = dimension['Value']
                    break

        # Extract instance name from alarm name
        name_patterns = [
            r'.*/([^/i][^/]+?)(?=/(?:i-|$))',
            r'.*/([^/]+?)(?=/\w+-\w+/?$)',
            r'MSP/[^/]+/[^/]+/EC2/([^/]+)/',
            r'/([^/+][^/]*[^/+])(?=/\w+Utilization)',
            r'-\s*([^-/]+?)(?=\s*-\s*OK|\s*-\s*Insufficient)',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, alarm_name, re.IGNORECASE)
            if match:
                potential_name = match.group(1).strip()
                # Filter out obvious non-names
                exclude_terms = ['cpu', 'memory', 'disk', 'status', 'mumbai', 'high', 
                               'utilization', 'check', 'alerts', 'non-prod', 'prod']
                if (potential_name and 
                    not any(term in potential_name.lower() for term in exclude_terms) and
                    len(potential_name) > 3 and
                    not potential_name.startswith('i-')):
                    instance_name = potential_name
                    break
        
        return instance_id, instance_name

    def get_instance_name_from_ec2(self, instance_id):
        """
        Get instance name from EC2 tags
        """
        try:
            response = self.ec2.describe_instances(InstanceIds=[instance_id])
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    for tag in instance.get('Tags', []):
                        if tag['Key'] == 'Name':
                            return tag['Value']
        except Exception as e:
            logger.warning(f"Could not get instance name for {instance_id}: {e}")
        return None

    def categorize_metric(self, metric_name, alarm_name):
        """
        Categorize metrics into CPU, Memory, Disk, Status, or Other
        """
        metric_name_lower = metric_name.lower() if metric_name else ''
        alarm_name_lower = alarm_name.lower()
        
        combined_check = metric_name_lower + ' ' + alarm_name_lower
        
        if any(x in combined_check for x in ['cpu', 'processor']):
            return 'CPU'
        elif any(x in combined_check for x in ['memory', 'mem', 'ram']):
            return 'Memory'
        elif any(x in combined_check for x in ['disk', 'storage', 'volume']):
            return 'Disk'
        elif any(x in combined_check for x in ['status', 'health', 'check', 'healthy']):
            return 'Status'
        else:
            return 'Other'

    def process_alarms(self, alarms):
        """
        Process alarms and extract required information
        """
        processed_data = []
        instance_id_map = {}  # Map instance IDs to names
        
        logger.info("Processing alarms and extracting instance information...")
        
        for alarm in alarms:
            alarm_name = alarm['AlarmName']
            alarm_state = alarm['StateValue']
            namespace = alarm.get('Namespace', '')
            metric_name = alarm.get('MetricName', '')
            dimensions = alarm.get('Dimensions', [])
            
            # Extract instance information
            instance_id, instance_name = self.extract_instance_info(alarm_name, namespace, metric_name, dimensions)
            
            # Get instance name from EC2 if we have instance ID but no name
            if instance_id and instance_id.startswith('i-') and not instance_name:
                if instance_id not in instance_id_map:
                    instance_id_map[instance_id] = self.get_instance_name_from_ec2(instance_id)
                instance_name = instance_id_map[instance_id]
            
            # If we still don't have a name, create a placeholder
            if not instance_name and instance_id:
                instance_name = f"Instance-{instance_id[-8:]}"
            elif not instance_name and not instance_id:
                # Try to extract any identifiable name from alarm name
                name_match = re.search(r'.*/([^/]+?)(?=/\w+Utilization|$)', alarm_name)
                if name_match:
                    instance_name = name_match.group(1)
                else:
                    instance_name = "Unknown-Resource"
            
            # Categorize the metric
            metric_category = self.categorize_metric(metric_name, alarm_name)
            
            processed_data.append({
                'instance_id': instance_id or 'N/A',
                'instance_name': instance_name,
                'alarm_name': alarm_name,
                'metric_name': metric_name or 'N/A',
                'metric_category': metric_category,
                'alarm_state': alarm_state,
                'namespace': namespace
            })
        
        return processed_data

    def create_excel_report(self, processed_data, output_file='cloudwatch_alarms_report.xlsx'):
        """
        Create Excel report with the required schema
        """
        try:
            # Create DataFrame
            df = pd.DataFrame(processed_data)
            
            if df.empty:
                logger.warning("No data to write to Excel")
                return False
            
            # Sort by instance name and metric category
            df = df.sort_values(['instance_name', 'instance_id', 'metric_category', 'metric_name'])
            
            # Create Excel writer
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                
                # Summary sheet
                summary_data = {
                    'Metric Category': ['CPU', 'Memory', 'Disk', 'Status', 'Other', 'Total'],
                    'Count': [
                        len(df[df['metric_category'] == 'CPU']),
                        len(df[df['metric_category'] == 'Memory']),
                        len(df[df['metric_category'] == 'Disk']),
                        len(df[df['metric_category'] == 'Status']),
                        len(df[df['metric_category'] == 'Other']),
                        len(df)
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                # State summary
                state_summary = df['alarm_state'].value_counts().reset_index()
                state_summary.columns = ['Alarm State', 'Count']
                state_summary.to_excel(writer, sheet_name='State Summary', index=False)
                
                # Detailed sheet
                df.to_excel(writer, sheet_name='Alarm Details', index=False)
                
                # Create a pivot view for better readability
                pivot_df = df.pivot_table(
                    index=['instance_name', 'instance_id', 'metric_category'],
                    values='alarm_state',
                    aggfunc='count',
                    fill_value=0
                ).reset_index()
                pivot_df.columns = ['Instance Name', 'Instance ID', 'Metric Category', 'Alarm Count']
                pivot_df.to_excel(writer, sheet_name='Instance Summary', index=False)
                
                # Formatting - Add instance-wise grouping
                self._create_instance_wise_sheet(df, writer)
            
            logger.info(f"Excel report generated: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating Excel report: {e}")
            return False

    def _create_instance_wise_sheet(self, df, writer):
        """
        Create a sheet with instance-wise alarm grouping
        """
        try:
            # Group by instance
            grouped_data = []
            
            for (instance_name, instance_id), group in df.groupby(['instance_name', 'instance_id']):
                instance_alarms = []
                
                for _, row in group.iterrows():
                    instance_alarms.append({
                        'Alarm': row['alarm_name'],
                        'Metric': row['metric_name'],
                        'Category': row['metric_category'],
                        'State': row['alarm_state']
                    })
                
                # Add instance header
                if instance_id != 'N/A':
                    grouped_data.append({
                        'Instance ID/Name': f'Instance ID: {instance_id}',
                        'Alarm Name': '',
                        'Metric Name': '',
                        'State': '',
                        'Category': ''
                    })
                
                grouped_data.append({
                    'Instance ID/Name': f'Instance name: {instance_name}',
                    'Alarm Name': '',
                    'Metric Name': '',
                    'State': '',
                    'Category': ''
                })
                
                # Add alarms for this instance
                for alarm in instance_alarms:
                    grouped_data.append({
                        'Instance ID/Name': '',
                        'Alarm Name': alarm['Alarm'],
                        'Metric Name': alarm['Metric'],
                        'State': alarm['State'],
                        'Category': alarm['Category']
                    })
                
                # Add empty row for separation
                grouped_data.append({
                    'Instance ID/Name': '',
                    'Alarm Name': '',
                    'Metric Name': '',
                    'State': '',
                    'Category': ''
                })
            
            instance_wise_df = pd.DataFrame(grouped_data)
            instance_wise_df.to_excel(writer, sheet_name='Instance Wise View', index=False)
            
        except Exception as e:
            logger.error(f"Error creating instance-wise sheet: {e}")

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
        
        logger.info("Processing alarm data...")
        processed_data = self.process_alarms(alarms)
        
        logger.info("Creating Excel report...")
        success = self.create_excel_report(processed_data, output_file)
        
        if success:
            logger.info(f"Report successfully generated: {output_file}")
            logger.info(f"Total alarms processed: {len(processed_data)}")
            
            # Print summary to console
            self.print_summary(processed_data)
            
        return success

    def print_summary(self, processed_data):
        """
        Print summary to console
        """
        df = pd.DataFrame(processed_data)
        
        print(f"\n{'='*60}")
        print(f"CLOUDWATCH ALARMS SUMMARY")
        print(f"{'='*60}")
        print(f"Total Alarms: {len(processed_data)}")
        print(f"{'='*60}")
        
        # Count by state
        state_counts = df['alarm_state'].value_counts()
        for state, count in state_counts.items():
            print(f"{state}: {count}")
        
        print(f"{'='*60}")
        
        # Count by category
        category_counts = df['metric_category'].value_counts()
        for category, count in category_counts.items():
            print(f"{category} Alarms: {count}")
        
        print(f"{'='*60}")
        
        # Unique instances
        unique_instances = df[df['instance_id'] != 'N/A']['instance_id'].nunique()
        unique_instance_names = df['instance_name'].nunique()
        print(f"Unique Instance IDs: {unique_instances}")
        print(f"Unique Instance Names: {unique_instance_names}")
        
        print(f"{'='*60}")
        
        # Show some example entries
        print("\nSAMPLE ENTRIES:")
        print(f"{'='*60}")
        for i, row in df.head(10).iterrows():
            instance_display = row['instance_id'] if row['instance_id'] != 'N/A' else row['instance_name']
            print(f"{instance_display} - {row['metric_category']} - {row['alarm_name'][:50]}... - {row['alarm_state']}")

def setup_argparse():
    """
    Set up command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Generate CloudWatch Alarms Report for AWS EC2 Instances',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Use default AWS credentials and region
  python cloudwatch_alarm_report.py
  
  # Use specific AWS profile
  python cloudwatch_alarm_report.py --profile my-profile
  
  # Use specific region
  python cloudwatch_alarm_report.py --region us-east-1
  
  # Use profile and custom output file
  python cloudwatch_alarm_report.py --profile production --output my_report.xlsx
  
  # Use different region with profile
  python cloudwatch_alarm_report.py --profile dev-account --region eu-west-1
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
            print("\n✅ Report generation completed successfully!")
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
