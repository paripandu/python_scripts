import boto3
import csv
import argparse
import sys
import pandas as pd

# ---------- Alarm Settings ----------
CSV_FILE = "lambda_functions.csv"
SNS_ARN = "arn:aws:sns:eu-west-2:52xxxxxxx:MSP_Alarm"
EXCEL_OUTPUT = "Lambda_Duration_Alarms_Output.xlsx"

# ---------- Read Functions from CSV ----------
def read_lambda_functions_from_csv(file_name):
    functions = []
    try:
        with open(file_name, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                fn = row.get("FunctionName", "").strip()
                if fn:
                    functions.append(fn)
    except FileNotFoundError:
        print(f"\u274c CSV file '{file_name}' not found in the current directory.")
        sys.exit(1)
    return functions

# ---------- Create Alarms ----------
def create_cloudwatch_alarms(cloudwatch, lambda_functions):
    output_rows = []
    for function_name in lambda_functions:
        for threshold, level in [(250, "WARNING"), (500, "CRITICAL")]:
            alarm_name = f"MSP/AWS/PROD/Lambda/{function_name}/DURATION_HIGH/London-{level}"
            try:
                cloudwatch.put_metric_alarm(
                    AlarmName=alarm_name,
                    MetricName="Duration",
                    Namespace='AWS/Lambda',
                    Statistic="Average",
                    Period=300,
                    EvaluationPeriods=1,
                    Threshold=threshold,
                    ComparisonOperator="GreaterThanThreshold",
                    AlarmActions=[SNS_ARN],
                    Dimensions=[
                        {
                            'Name': 'FunctionName',
                            'Value': function_name
                        }
                    ],
                    TreatMissingData='missing',
                    ActionsEnabled=True
                )
                print(f"\u2705 Created alarm: {alarm_name}")
                output_rows.append({
                    "FunctionName": function_name,
                    "AlarmName": alarm_name,
                    "Threshold": threshold,
                    "AlarmLevel": level,
                    "Status": "Created"
                })
            except Exception as e:
                print(f"\u274c Failed to create alarm: {alarm_name} - Error: {e}")
                output_rows.append({
                    "FunctionName": function_name,
                    "AlarmName": alarm_name,
                    "Threshold": threshold,
                    "AlarmLevel": level,
                    "Status": f"Failed - {e}"
                })

    # Export to Excel
    df = pd.DataFrame(output_rows)
    df.to_excel(EXCEL_OUTPUT, index=False)
    print(f"\n\ud83d\udcc4 Alarm creation summary written to '{EXCEL_OUTPUT}'")

# ---------- Main ----------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Duration alarms for Lambda functions from CSV")
    parser.add_argument("--profile", required=True, help="AWS CLI profile name to use")
    args = parser.parse_args()

    try:
        session = boto3.Session(profile_name=args.profile)
        cloudwatch = session.client("cloudwatch")
    except Exception as e:
        print(f"\u274c Failed to initialize AWS session with profile '{args.profile}': {e}")
        sys.exit(1)

    functions = read_lambda_functions_from_csv(CSV_FILE)
    print(f"\n\ud83d\udd0d Found {len(functions)} functions in '{CSV_FILE}'")
    create_cloudwatch_alarms(cloudwatch, functions)

