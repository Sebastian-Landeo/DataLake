#!/bin/bash

# Define the directory to store the .jar files
JARS_DIR="./jars"

# Create the directory if it doesn't exist
mkdir -p "$JARS_DIR"

# Array of required .jar files with their download URLs
declare -A jars
jars=(
  ["hadoop-aws-3.3.4.jar"]="https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar"
  ["aws-java-sdk-1.11.534.jar"]="https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk/1.11.534/aws-java-sdk-1.11.534.jar"
  ["aws-java-sdk-core-1.11.534.jar"]="https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-core/1.11.534/aws-java-sdk-core-1.11.534.jar"
  ["aws-java-sdk-dynamodb-1.11.534.jar"]="https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-dynamodb/1.11.534/aws-java-sdk-dynamodb-1.11.534.jar"
  ["aws-java-sdk-kms-1.11.534.jar"]="https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-kms/1.11.534/aws-java-sdk-kms-1.11.534.jar"
  ["aws-java-sdk-s3-1.11.534.jar"]="https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-s3/1.11.534/aws-java-sdk-s3-1.11.534.jar"
  ["httpclient-4.5.3.jar"]="https://repo1.maven.org/maven2/org/apache/httpcomponents/httpclient/4.5.3/httpclient-4.5.3.jar"
  ["joda-time-2.9.9.jar"]="https://repo1.maven.org/maven2/joda-time/joda-time/2.9.9/joda-time-2.9.9.jar"
)

# Download each .jar file if it doesn't already exist
for jar in "${!jars[@]}"; do
  if [ ! -f "$JARS_DIR/$jar" ]; then
    echo "Downloading $jar..."
    curl -L -o "$JARS_DIR/$jar" "${jars[$jar]}"
  else
    echo "$jar already exists, skipping download."
  fi
done

echo "All required .jar files are present in the '$JARS_DIR' directory."

