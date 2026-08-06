import sys
sys.path.append('/root/data-etl-pipelines/scripts/docai/eldorado/preprocessor/')
from utils import get_snowflake_connection, get_s3_credentials, get_notification_parameters
sys.path.append('/root/data-etl-pipelines/scripts/configs/')
import config
import datetime
from argparse import ArgumentParser
import boto3
import time

# usage:
# python move_file.py -env=qa -claim_type=institutional

DEFAULT_ROOT_DIR="/root/data-etl-pipelines"
current_date = datetime.date.today().strftime("%Y%m%d")
log_file_path = "{DEFAULT_ROOT}/logs/{CURRENT_DATE}_move_file.log".format(DEFAULT_ROOT=DEFAULT_ROOT_DIR,CURRENT_DATE=current_date)
logger = config.console_and_file_logger("move_file", log_file_path)

parser = ArgumentParser(description="Script for appending columns to import schema of snowflake databases")
parser.add_argument("-env", type=str, required=True, choices=['qa', 'stage', 'pilot', 'prod'] , help="env.")
parser.add_argument("-claim_type", type=str, required=True, choices=['dental', 'institutional', 'professional'], help="Claim type.")
args = parser.parse_args()

S3BUCKET = f'{args.env}-enterprise-data-lake-refined'
ELDORADO_FOLDER = "Eldorado_Vendor_Claims_Refined/"
ELDORADO_INBOUND_FOLDER = "Landing/"
ELDORADO_PROCESSED_FILE_FOLDER = "DocAI/"
ELDORADO_NON_PROCESSED_FILE_FOLDER = "Mphasis/"
year = "year="+time.strftime("%Y")
month="month="+time.strftime("%m")
day = "day="+time.strftime("%d")
claim_type = f'{args.claim_type}'


aws_key_id, aws_secret_key = get_s3_credentials(f'{args.env.upper()}')

s3_client = boto3.client(
    's3',
    aws_access_key_id=aws_key_id,
    aws_secret_access_key=aws_secret_key
)
s3_resource= boto3.resource(
    's3',
    aws_access_key_id=aws_key_id,
    aws_secret_access_key=aws_secret_key
)

INTEGRATION, RECIPIENTS = get_notification_parameters(f'{args.env.upper()}')

def move_successfully_processed_files(Con):
    f'''
        The function is reading results in DOC_AI.DOC_AI_VALIDATION for the given claim_type and look for files which have been 
        validated on current date and the value of the column passed_validation is true.
        For every file that matches above requirements:
        - the function create and upload file under ELDORADO_PROCESSED_FILE_FOLDER/claim_type in json format
        - delete file from ELDORADO_INBOUND_FOLDER/claim_type
        If the file is validated multiple times on a single day, it will read last one result.
        The function does not return any values.
        :param Con: snowflake connection object
    '''
    logger.info(f"== DOC AI {args.env.upper()} {args.claim_type} moving successfully processed files has started. ==")

    try:
           # get list of successfully processed files
           sql = f"""SELECT CURR.TABLE_NAME, SUBSTR(CURR.FILE_NAME,27) AS FILE_NAME, REPLACE(SUBSTR(CURR.FILE_NAME,27), '.tif','') AS NEW_FILE_NAME, CURR.ID AS ID, FILE_NAME AS PATH_FILE_NAME,CURR.FORMULA_FOR_VALUE, MD5_HASH, DW_CREATED_DATE
           FROM DOC_AI.DOC_AI_VALIDATION CURR
           INNER JOIN (SELECT ID, ROW_NUMBER() OVER(PARTITION BY TABLE_NAME, FILE_NAME, MD5_HASH ORDER BY DW_CREATED_DATE DESC) AS RN
           FROM DOC_AI.DOC_AI_VALIDATION
           WHERE
           DW_CREATED_DATE::DATE=CURRENT_DATE AND
           UPPER(CLAIM_TYPE)=UPPER('{args.claim_type.upper()}')
           AND POSTPROCESSED=FALSE
           ) TBL ON CURR.ID=TBL.ID
           WHERE TBL.RN=1
           AND CURR.PASSED_VALIDATION = TRUE;"""
           files = Con.cursor().execute(f"{sql}")

           # for every successfully processed file, upload file in json format in a new location and archive it
           for file in files:
               logger.info(f"== Table: {file[0]} file: {file[1]}. ==")
               path = f'{ELDORADO_FOLDER}{claim_type.capitalize()}/{file[4]}'
               target_dir=f'{ELDORADO_FOLDER}{ELDORADO_PROCESSED_FILE_FOLDER}{claim_type.capitalize()}/{year}/{month}/{day}'

               sql=f"""COPY INTO 's3://{S3BUCKET}/{target_dir}/{file[2]}'
           FROM (
                SELECT OBJECT_CONSTRUCT(*) 
                FROM (
                    SELECT {file[5]}, 
                    SUBSTRING(FILE_NAME,27) AS FILENAME 
                    FROM DOC_AI.{file[0]} 
                    WHERE FILE_NAME='{file[4]}' 
                      AND MD5_HASH='{file[6]}' 
                      AND DW_CREATED_DATE::DATE='{file[7]}'::DATE
                      )
                )
           CREDENTIALS = ( aws_key_id = '{aws_key_id}' aws_secret_key = '{aws_secret_key}')
           FILE_FORMAT = (TYPE=JSON COMPRESSION = NONE)
           OVERWRITE = TRUE;"""
               Con.cursor().execute(f"{sql}")
               logger.info(f"== The file {file[1]} has been successfully converted in json format and loaded into s3://{S3BUCKET}/{ELDORADO_FOLDER}{ELDORADO_PROCESSED_FILE_FOLDER}{claim_type.capitalize()}/{year}/{month}/{day}/{file[2]}.json.gz. ==")
               s3_client.delete_object(Bucket=f'{S3BUCKET}', Key=f'{path}')
               Con.cursor().execute(f"UPDATE DOC_AI.DOC_AI_VALIDATION SET POSTPROCESSED=TRUE, DW_UPDATED_DATE=CURRENT_TIMESTAMP() WHERE ID={file[3]};")
               logger.info(f"== The file {file[1]} has been successfully deleted from s3://{S3BUCKET}/{path} ==")
    except Exception as error:
        logger.info(f"== DOC AI {args.env.upper()} {args.claim_type} moving successfully processed files has failed. ==")
        logger.error(f"== Error: {error} ==")
        Con.cursor().execute(f"CALL SYSTEM$SEND_EMAIL('{INTEGRATION}','{RECIPIENTS}', '{args.env.upper()} DOC AI image postprocessing failed','Check the logs for step move processed file ');")
        sys.exit(1)

    logger.info(f"== DOC AI {args.env.upper()} {args.claim_type} moving successfully processed file has been completed. ==\n")



def move_non_processed_files(Con):
    f'''
        The function is reading results in DOC_AI.DOC_AI_VALIDATION for the given claim_type and look for files which have been 
        validated on current date and the value of the column passed_validation is false.
        For every file that matches above requirements:
        - the function move file from ELDORADO_INBOUND_FOLDER/claim_type to ELDORADO_NON_PROCESSED_FILE_FOLDER/claim_type
        - send email alert with list of non-processed files
        If the file is validated multiple times on a single day, it will read last one result.
        The function does not return any values.
        :param Con: snowflake connection object
    '''
    logger.info(f"== DOC AI {args.env.upper()} {args.claim_type} moving non-processed files has started. ==")
    list_of_non_processed_files=""
    try:
        # get list of non-processed files
        sql = f"""SELECT CURR.TABLE_NAME, SUBSTR(CURR.FILE_NAME,27) AS FILE_NAME, CURR.ID AS ID, FILE_NAME AS FILE_PATH
           FROM DOC_AI.DOC_AI_VALIDATION CURR
           INNER JOIN (SELECT ID, ROW_NUMBER() OVER(PARTITION BY TABLE_NAME, FILE_NAME ORDER BY DW_CREATED_DATE DESC) AS RN
           FROM DOC_AI.DOC_AI_VALIDATION
           WHERE
           DW_CREATED_DATE::DATE=CURRENT_DATE AND
           UPPER(CLAIM_TYPE)=UPPER('{args.claim_type.upper()}')
           AND POSTPROCESSED=FALSE
           ) TBL ON CURR.ID=TBL.ID
           WHERE TBL.RN=1
           AND CURR.PASSED_VALIDATION = FALSE;"""
        files = Con.cursor().execute(f"{sql}")
        # TODO: check if unprocessed tiff files are being sent to mphasis folder
        # for every non-processed file, upload it in folder for non-processed files
        for file in files:
            logger.info(f"== Table: {file[0]} file: {file[1]}. ==")
            path = f'{ELDORADO_FOLDER}{claim_type.capitalize()}/{file[3]}'
            target_dir = f'{ELDORADO_FOLDER}{ELDORADO_NON_PROCESSED_FILE_FOLDER}{claim_type.capitalize()}/{year}/{month}/{day}/'

            s3_resource.Object(S3BUCKET,  f'{target_dir}{file[1]}').copy_from(CopySource=f'{S3BUCKET}/{path}')
            s3_client.delete_object(Bucket=f'{S3BUCKET}', Key=f'{path}')
            Con.cursor().execute(f"UPDATE DOC_AI.DOC_AI_VALIDATION SET POSTPROCESSED=TRUE, DW_UPDATED_DATE=CURRENT_TIMESTAMP() WHERE ID={file[2]};")
            logger.info(f"== The file {file[1]} has been successfully moved from s3://{S3BUCKET}/{path} to s3://{S3BUCKET}/{target_dir}{file[1]}. ==")
            list_of_non_processed_files = list_of_non_processed_files + file[1] + "\n"

    except Exception as error:
        logger.info(f"== DOC AI {args.env.upper()} {args.claim_type.upper()} moving non-processed files has failed. ==")
        logger.info(f"== Error: {error} ==")
        Con.cursor().execute(f"CALL SYSTEM$SEND_EMAIL('{INTEGRATION}','{RECIPIENTS}', '{args.env.upper()} DOC AI image postprocessing failed','Check the logs for step move non-processed file.');")
        sys.exit(1)
    Con.cursor().execute(f"CALL SYSTEM$SEND_EMAIL('{INTEGRATION}','{RECIPIENTS}', 'ALERT {args.env.upper()} {args.claim_type.upper()} DOC AI non-processed files','Please check the list for the files which did not pass the DOC AI validation:\n{list_of_non_processed_files} \n The files have been moved into s3 location:3://{S3BUCKET}/{target_dir}.');")
    logger.info(f"== DOC AI {args.env.upper()} {args.claim_type} moving non-processed file has been completed. ==\n")


def main():
    con, ds_name = get_snowflake_connection('{env}'.format(env=args.env.upper()))
    move_successfully_processed_files(con)
    print("\n\n")
    move_non_processed_files(con)


if __name__ == '__main__':
    main()