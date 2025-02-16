#!/bin/bash

# Check initial disk usage
echo "Checking initial disk usage..."
df -TH

# Define the mount point to monitor
DISK_MOUNT_POINT="/"

# Set disk usage threshold (80%)
DISK_USAGE_THRESHOLD=80

# Navigate to the Prometheus directory
PROMETHEUS_DIR="/var/lib/prometheus"
echo "Navigating to: $PROMETHEUS_DIR"
cd "$PROMETHEUS_DIR" || { echo "Failed to navigate to $PROMETHEUS_DIR"; exit 1; }

# Identify large folders
echo "Finding large folders..."
LARGE_FOLDERS=$(du -sh * | grep G | awk '{print $2}')
if [ -z "$LARGE_FOLDERS" ]; then
  echo "No large folders found. Exiting."
  exit 0
fi

echo "Large folders found:"
echo "$LARGE_FOLDERS"

echo "Please share the above details on the Hangout group and confirm whether to proceed with compression or deletion."
echo "Waiting for confirmation..."
read -p "Type 'yes' to continue or 'no' to exit: " CONFIRMATION
if [[ "$CONFIRMATION" != "yes" ]]; then
  echo "Operation aborted."
  exit 0
fi

# S3 Bucket base path
S3_BUCKET="s3://prometheus-files/non-prod"

# Process each large folder one by one
for FOLDER in $LARGE_FOLDERS; do
  # Check current disk usage
  CURRENT_USAGE=$(df -h "$DISK_MOUNT_POINT" | awk 'NR==2 {print $5}' | sed 's/%//')
  echo "Current disk usage: $CURRENT_USAGE%"

  # Stop processing if disk usage is below threshold
  if [ "$CURRENT_USAGE" -lt "$DISK_USAGE_THRESHOLD" ]; then
    echo "Disk usage is below $DISK_USAGE_THRESHOLD%. Stopping further uploads."
    break
  fi

  echo "Processing folder: $FOLDER"

  # Extract the folder's creation month and year
  FOLDER_CREATION_DATE=$(ls -ld --time-style="+%B-%Y" "$FOLDER" | awk '{print $6}')
  echo "Folder creation date: $FOLDER_CREATION_DATE"

  # Define the S3 destination dynamically
  S3_FOLDER="$S3_BUCKET/$FOLDER_CREATION_DATE/$FOLDER/"
  echo "Uploading $FOLDER to S3: $S3_FOLDER"

  # Upload the folder to S3
  aws s3 cp "$FOLDER" "$S3_FOLDER" --recursive

  if [ $? -eq 0 ]; then
    echo "Successfully copied $FOLDER to $S3_FOLDER"

    # Remove the folder after successful upload
    echo "Removing folder: $FOLDER"
    rm -rfv "$FOLDER"

    # Check for processes holding deleted files
    echo "Checking for processes holding deleted files..."
    DELETED_PIDS=$(lsof | egrep "deleted|COMMAND" | grep "$FOLDER" | awk '{print $2}')
    if [ -n "$DELETED_PIDS" ]; then
      echo "Processes holding deleted files:"
      echo "$DELETED_PIDS"

      # Kill the processes
      for PID in $DELETED_PIDS; do
        echo "Killing process ID: $PID"
        kill -9 "$PID"
      done
    else
      echo "No processes holding deleted files for $FOLDER."
    fi
  else
    echo "Failed to copy $FOLDER to S3. Skipping deletion."
  fi

  # Recheck disk usage after moving one folder
  df -TH
done

# Final disk usage check
echo "Final disk usage after cleanup:"
df -TH
