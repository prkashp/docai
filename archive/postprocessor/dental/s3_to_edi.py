import boto3
import json
import os
import sys
import uuid
import gzip
import io
import time
import requests
from datetime import datetime
from json_standardization import transform_document
sys.path.append('/root/data-etl-pipelines/scripts/docai/eldorado/preprocessor/')
from utils import decrypt_password ,get_s3_credentials, get_snowflake_connection
import logging

logging.basicConfig(
    format='%(asctime)s %(levelname)-4s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

transactionSettingId = '005010X224A2-837' # Dental Guide - Health Care Claim: Dental (X224A2)
partnershipId = 'local_PH_HC_TEST' # Could be changed in future
# input_prefix = "Eldorado_Vendor_Claims_Refined/DocAI/Dental/" # Relative path for JSONs
# output_prefix = "Eldorado_Vendor_Claims_Refined/Outbound/Dental/" # Relative path for edi files
input_prefix = "Eldorado_Vendor_Claims/edi-test/DocAI/Dental/" # Relative path for JSONs
output_prefix = "Eldorado_Vendor_Claims/edi-test/Outbound/Dental/" # Relative path for edi files

def get_api_key(env):
    """
    Retrieve and decrypt the Stedi API key for the given environment.
    Args:
        env (str): Environment name (e.g., 'prod').
    Returns:
        str: Decrypted API key.
    """
    try:
        data_source = "/root/data-etl-pipelines/scripts/configs/data_source_json/{env}_data_source.json".format(env=env.lower())

        with open(data_source, 'r') as obj:
            creds = json.load(obj)
        api_key = decrypt_password(creds['stedi']['api_key'], creds['configs']["salt"],creds['configs']["secret_key"])

        return api_key

    except Exception as e:
        log.error(f"Error decrypting api key. Error: {e}")

def list_json_files_in_s3(bucket, prefix, s3_client):
    """
    List all JSON files in the specified S3 bucket and prefix.
    Args:
        bucket (str): Name of the S3 bucket.
        prefix (str): S3 prefix/path to search in.
        s3_client (boto3.client): Boto3 S3 client object.
    Returns:
        list: List of JSON file keys.
    """
    paginator = s3_client.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)

    json_files = []
    for page in page_iterator:
        contents = page.get('Contents', [])
        for obj in contents:
            key = obj['Key']
            if key.endswith('.json'):
                json_files.append(key)
    return json_files

def download_json_from_s3(bucket, key, s3_client):
    """
    Download and return a JSON object from S3. Supports .json and .json.gz files.
    Args:
        bucket (str): S3 bucket name.
        key (str): S3 object key.
        s3_client (boto3.client): Boto3 S3 client.
    Returns:
        dict: Parsed JSON content.
    Raises:
        ValueError: If file type is unsupported.
    """
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    content = obj['Body'].read()

    if key.endswith('.json.gz'):
        # Decompress gzip content
        with gzip.GzipFile(fileobj=io.BytesIO(content)) as gz:
            decompressed_bytes = gz.read()
        json_str = decompressed_bytes.decode('utf-8')
    elif key.endswith('.json'):
        # Plain JSON file
        json_str = content.decode('utf-8')
    else:
        raise ValueError(f"Unsupported file type for key: {key}")

    return json.loads(json_str)

def handle_response(response):
    """
    Handle and log HTTP response from Stedi API. Exits on error codes.
    Args:
        response (requests.Response): HTTP response object.
    """
    if response.status_code == 200:
        # Success: process the response content
        log.info("200 OK. Success!")
        data = response.json()  # or response.text if not JSON
        # Process data as needed
        log.info(data)

    elif 400 <= response.status_code < 500:
        # Client error: report, delay, then exit
        log.error(f"Client Error: {response.status_code}")
        log.error(f"Response: {response.text}")
        time.sleep(5)  # Delay for 5 seconds before exiting
        sys.exit(1)

    elif 500 <= response.status_code < 600:
        # Server error: report, delay, then exit
        log.error(f"Server Error: {response.status_code}")
        log.error(f"Response: {response.text}")
        time.sleep(10)  # Delay for 10 seconds before exiting
        sys.exit(1)

    else:
        # Unexpected status code: exit immediately
        log.error(f"Unexpected Status Code: {response.status_code}")
        log.error(f"Response: {response.text}")
        sys.exit(1)

def post_outbound_transaction(env, transformed_json, filename="my-test-output-file.edi"):
    """
    Post the transformed JSON as an outbound transaction to Stedi API.
    Args:
        env (str): Environment name.
        transformed_json (dict): Transformed JSON payload.
        filename (str): Name for the outbound EDI file.
    Returns:
        requests.Response: HTTP response from Stedi API.
    """
    url = f"https://core.us.stedi.com/2023-08-01/partnerships/{partnershipId}/transactions/{transactionSettingId}"

    body = {
        "filename": filename,
        "transaction": transformed_json
    }
    response = requests.request("POST", url, json = body, headers = {
        "Authorization": get_api_key(env),
        "Content-Type": "application/json"
    })

    return response

def download_edi_file(execution_id, api_key):
    """
    Download the EDI file content from Stedi API using the execution ID.
    Args:
        execution_id (str): File execution ID from Stedi.
        api_key (str): Stedi API key.
    Returns:
        bytes: EDI file content.
    """
    url = f"https://core.us.stedi.com/2023-08-01/executions/{execution_id}/output"

    headers = {
        "Authorization": api_key
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.content


def upload_to_s3(bucket, key, file_bytes, s3_client):
    """
    Upload a file to S3.
    Args:
        bucket (str): S3 bucket name.
        key (str): S3 object key.
        file_bytes (bytes): File content in bytes.
        s3_client (boto3.client): Boto3 S3 client.
    """
    s3_client.put_object(Bucket=bucket, Key=key, Body=file_bytes)
    log.info(f"Uploaded EDI file to s3://{bucket}/{key}")

def updated_snowflake_logs(con, transaction_regex, translated, log_message=None):
    """
    Update the TRANSLATED and logs columns in DOC_AI.DOC_AI_VALIDATION table for matching records.
    Args:
        con: Snowflake DB connection object.
        transaction_regex (str): Regex pattern to match FILE_NAME.
        translated (bool): Value to set for TRANSLATED column (True/False).
        log_message (str, optional): Error message to log. If None, logs success.
    Returns:
        int: 0 if successful, exits on error.
    """
    try:
        translated_str = 'TRUE' if translated else 'FALSE'
        message = log_message if log_message else 'success'
        # Use Snowflake's OBJECT_CONSTRUCT and CURRENT_TIMESTAMP() for VARIANT
        sql = f"""
            UPDATE DOC_AI.DOC_AI_VALIDATION
            SET TRANSLATED={translated_str},
                logs=OBJECT_CONSTRUCT('message', '{message}', 'timestamp', CURRENT_TIMESTAMP())
            WHERE CLAIM_TYPE='DENTAL'
              AND FILE_NAME REGEXP '{transaction_regex}';
        """
        results = con.cursor().execute(sql)
        log.info(f"Updated TRANSLATED={translated_str}, logs message='{message}' for records matching regex: {transaction_regex}")
        if hasattr(results, 'rowcount'):
            log.info(f"Rows affected: {results.rowcount}")
    except Exception as e:
        log.error(f"Error while updating results: {e}")
        sys.exit(1)
    return 0

def process_transactions(env):
    """
    Main ETL process for converting dental JSONs to EDI, uploading results, and updating logs.
    Args:
        env (str): Environment name.
    Returns:
        int: 0 if successful, exits on error.
    """
    bucket = f"{env}-enterprise-data-lake-refined"

    aws_access_key, aws_secret_key = get_s3_credentials(env)
    s3 = boto3.client('s3',
                      region_name='us-east-1',
                      aws_access_key_id=aws_access_key,
                      aws_secret_access_key=aws_secret_key)

    json_files = list_json_files_in_s3(bucket, input_prefix, s3)
    log.info(f"Found {len(json_files)} JSON files in s3://{bucket}/{input_prefix}")

    transactions = {}
    transactions_regex = ""

    if json_files:
        con, _ = get_snowflake_connection(env)
        for idx, key in enumerate(json_files, start=1):
            log.info(f"[{idx}/{len(json_files)}] Processing {key}...")

            try:
                raw_doc = download_json_from_s3(bucket, key, s3)
            except Exception as e:
                log.error(f"ERROR downloading/parsing {key}: {e}")
                sys.exit(1)

            try:
                transformed = transform_document(raw_doc)
            except Exception as e:
                log.error(f"ERROR transforming {key}: {e}")
                # Move file to error folder
                error_key = key.replace("DocAI/Dental/", "DocAI/DLQ/Dental/")
                try:
                    s3.copy_object(Bucket=bucket, CopySource=f"{bucket}/{key}", Key=error_key)
                    s3.delete_object(Bucket=bucket, Key=key)
                    log.info(f"Moved file {key} to {error_key} due to transformation error.")
                except Exception as move_err:
                    log.error(f"Failed to move file {key} to error folder: {move_err}")
                # Update snowflake log with translated=False
                try:
                    updated_snowflake_logs(con, raw_doc['FILENAME'], False, log_message=e)
                except Exception as log_err:
                    log.error(f"Failed to update snowflake log for {key}: {log_err}")
                # Do NOT sys.exit(1); continue processing other files
                continue

            transactions_regex += "|" if transactions_regex != "" else ""
            transactions_regex += f".*{raw_doc['FILENAME']}.*"

            file_name = raw_doc['FILENAME'].replace('.tif','') + '.x12'

            response = post_outbound_transaction(env, transformed, file_name)
            handle_response(response)

            execution_id = response.json()['fileExecutionId']

            transactions[file_name] = execution_id

        now = datetime.now()
        year, month, day = now.strftime("%Y"), now.strftime("%m"), now.strftime("%d")
        relative_path = f'year={year}/month={month}/day={day}/'

        time.sleep(2) # try 2 secs to get the file

        for key, value in transactions.items():
            try:
                edi_file_content = download_edi_file(value, get_api_key(env))
                log.info(f"Downloaded EDI file of size: {len(edi_file_content)} bytes")

                upload_to_s3(bucket, output_prefix+relative_path+key, edi_file_content, s3)
                log.info("Process completed successfully.")

            except Exception as e:
                log.error(f"Error: {e}")
                sys.exit(1)
        try:
            updated_snowflake_logs(con,transactions_regex, True)
        except Exception as e:
            log.error(f"Error updating snowflake logs due to {e}")
            sys.exit(1)

        try:
            for path in json_files:
                s3.copy_object(Bucket=bucket, CopySource=bucket+'/'+path, Key=path.replace("DocAI/Dental/", "DocAI/Archive/Dental/"))
                s3.delete_object(Bucket=bucket, Key=path)
        except Exception as e:
            log.error(f"Error moving file: {e}")
            sys.exit(1)

        return 0
    else:
        log.error("No Json File found on S3 path: " + input_prefix)
        sys.exit(1)



def main():
    """
    Entry point for running the ETL process via command line.
    """
    if len(sys.argv) < 1:
        log.info("Usage: python s3_to_edi.py <environment>")
        sys.exit(1)
    env = sys.argv[1]
    process_transactions(env)


if __name__ == "__main__":
    main()
