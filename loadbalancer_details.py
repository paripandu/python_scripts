import boto3
import argparse
import openpyxl

def parse_args():
    parser = argparse.ArgumentParser(description='Fetch active/inactive AWS Load Balancers with details')
    parser.add_argument('--profile', help='baxa-nonprod', required=True)
    parser.add_argument('--region', help='ap-south-1', default='us-east-1')
    parser.add_argument('--output', help='Output Excel file name', default='load_balancer_status.xlsx')
    return parser.parse_args()

def get_load_balancer_status(profile_name, region_name):
    session = boto3.Session(profile_name='baxa-nonprod', region_name='ap-south-1')
    elbv2 = session.client('elbv2')

    lbs = elbv2.describe_load_balancers()
    lb_list = lbs['LoadBalancers']

    result = []

    for lb in lb_list:
        lb_name = lb['LoadBalancerName']
        dns_name = lb['DNSName']
        lb_arn = lb['LoadBalancerArn']
        vpc_id = lb['VpcId']
        lb_type = lb['Type']
        ip_address_type = lb['IpAddressType']
        lb_id = lb_arn.split('/')[-1]  # or you can use the full ARN if you prefer

        listeners = elbv2.describe_listeners(LoadBalancerArn=lb_arn)
        active = False

        for listener in listeners['Listeners']:
            rules = elbv2.describe_rules(ListenerArn=listener['ListenerArn'])

            for rule in rules['Rules']:
                for action in rule['Actions']:
                    if action['Type'] == 'forward':
                        target_group_arn = action['TargetGroupArn']

                        target_health = elbv2.describe_target_health(TargetGroupArn=target_group_arn)
                        for target in target_health['TargetHealthDescriptions']:
                            health_state = target['TargetHealth']['State']
                            if health_state == 'healthy':
                                active = True
                                break
                        if active:
                            break
                if active:
                    break
            if active:
                break

        status = "Active" if active else "Inactive"
        result.append({
            'Region': region_name,
            'LoadBalancerName': lb_name,
            'DNSName': dns_name,
            'Status': status,
            'VpcId': vpc_id,
            'LoadBalancerType': lb_type,
            'IpAddressType': ip_address_type,
            'LoadBalancerId': lb_id
        })

    return result

def write_to_excel(lb_status_list, output_file):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "LoadBalancer Status"

    # Write header
    headers = ["Region", "LoadBalancerName", "DNSName", "Status", "VpcId", "LoadBalancerType", "IpAddressType", "LoadBalancerId"]
    sheet.append(headers)

    # Write data
    for lb in lb_status_list:
        sheet.append([
            lb['Region'],
            lb['LoadBalancerName'],
            lb['DNSName'],
            lb['Status'],
            lb['VpcId'],
            lb['LoadBalancerType'],
            lb['IpAddressType'],
            lb['LoadBalancerId']
        ])

    workbook.save(output_file)
    print(f"\n✅ Load Balancer status saved to '{output_file}'")

if __name__ == "__main__":
    args = parse_args()

    lb_status_list = get_load_balancer_status(args.profile, args.region)

    # Print on terminal
    print(f"{'Region':<15} {'LoadBalancerName':<30} {'DNSName':<60} {'Status':<10} {'VpcId':<20} {'Type':<10} {'IP Type':<15} {'ID':<30}")
    print("-" * 200)
    for lb in lb_status_list:
        print(f"{lb['Region']:<15} {lb['LoadBalancerName']:<30} {lb['DNSName']:<60} {lb['Status']:<10} {lb['VpcId']:<20} {lb['LoadBalancerType']:<10} {lb['IpAddressType']:<15} {lb['LoadBalancerId']:<30}")

    # Write to Excel
    write_to_excel(lb_status_list, args.output)

