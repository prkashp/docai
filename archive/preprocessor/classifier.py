import logging
import boto3
import sys
from utils import get_snowflake_connection
from utils import get_s3_credentials

# configuring logger
logging.basicConfig(
    format='%(asctime)s %(levelname)-4s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
env = sys.argv[1].lower()
bucket_name = f'{env}-enterprise-data-lake-refined'
landing_bucket_key = 'Eldorado_Vendor_Claims_Refined/Landing/'
bucket_key = 'Eldorado_Vendor_Claims_Refined/'
admin_table = 'INGESTION_CONTROL'

# Update cutoff here to filter scans based on OCRs
DENTAL_OCR_CUTOFF='0.85'
PROFESSIONAL_OCR_CUTOFF='0.0'
INSTITUTIONAL_OCR_CUTOFF='0.0'

def classify_files(con, database, schema, table):
    """
    This method fetch predicted results from landing_claim_type table and move file to different bucket keys
    :param con: snowflake connection object
    :param database: VP database name
    :param schema: DocAi schema name
    :param table: Claim type landing table name
    :return:
    """
    try:
        results=con.cursor().execute(f'''
        SELECT CASE WHEN UPPER(JSON_CONTENT:"FORM_TYPE"[0]:value::VARCHAR) LIKE '%HEALTH%' THEN 'Professional' 
                    WHEN UPPER(JSON_CONTENT:"FORM_TYPE"[0]:value::VARCHAR) LIKE '%DENTAL%' THEN 'Dental'
                ELSE 'Institutional' END AS TYPE, 
                FILE_NAME,
                JSON_CONTENT:"__documentMetadata":"ocrScore" as ocr
        FROM  {database}.{schema}.{table}
        WHERE DW_CREATED_DATE > (SELECT NVL(MAX(LAST_LOADED_TS),'0') 
                                    FROM {schema}.INGESTION_CONTROL 
                                   WHERE TABLE_NAME='{table}')
          AND ((TYPE='Dental' AND ocr>={DENTAL_OCR_CUTOFF}) 
           OR (TYPE='Professional' AND ocr>={PROFESSIONAL_OCR_CUTOFF})
           OR (TYPE NOT IN ('Dental', 'Professional') AND ocr>={INSTITUTIONAL_OCR_CUTOFF}));
        ''')
        log.info(f"Fetched results from {table}: {results.rowcount}")
    except Exception as error:
        log.error("Error getting file path results: " + str(error))
        sys.exit(1)
    else:
        source = bucket_name+'/'+landing_bucket_key
        aws_access_key, aws_secret_key = get_s3_credentials(env)
        s3 = boto3.client('s3',
                          region_name='us-east-1',
                          aws_access_key_id=aws_access_key,
                          aws_secret_access_key=aws_secret_key)
        professional_count, dental_count, institutional_count = 0, 0, 0
        for pair in results.fetchall():
            try:
                if pair[0]=='Professional':
                    s3.copy_object(Bucket=bucket_name, CopySource=source+pair[1], Key=bucket_key+'Professional/'+pair[1])
                    s3.delete_object(Bucket=bucket_name, Key=landing_bucket_key+pair[1])
                    professional_count += 1
                elif pair[0]=='Dental':
                    s3.copy_object(Bucket=bucket_name, CopySource=source+pair[1], Key=bucket_key+'Dental/'+pair[1])
                    s3.delete_object(Bucket=bucket_name, Key=landing_bucket_key+pair[1])
                    dental_count += 1
                else:
                    s3.copy_object(Bucket=bucket_name, CopySource=source+pair[1], Key=bucket_key+'Institutional/'+pair[1])
                    s3.delete_object(Bucket=bucket_name, Key=landing_bucket_key+pair[1])
                    institutional_count += 1
            except Exception  as error:
                log.warning("File is already moved or missing from source: "+str(pair)+" | Error: "+ str(error))

        log.info(f"Files moved to respective bucket keys - Professional:{professional_count}")
        log.info(f"Files moved to respective bucket keys - Dental:{dental_count}")
        log.info(f"Files moved to respective bucket keys - Institutional:{institutional_count}")
        try:

            con.cursor().execute(f"""
            INSERT INTO {database}.{schema}.{admin_table} (TABLE_NAME, LAST_LOADED_TS, FILES_MOVED)
            SELECT '{table}', 
                    (SELECT MAX(DW_CREATED_DATE) FROM {schema}.{table}), 
                    OBJECT_CONSTRUCT('dental_count', {dental_count}, 'institutional_count', {institutional_count}, 'professional_count', {professional_count}, 'created_date', current_timestamp())
            """)
            log.info(f"Logged metadata to {admin_table}")

        except Exception as error:
            log.error("Error inserting logs to admin table: " + str(error))
            sys.exit(1)

def main():
    if len(sys.argv) <= 1:
        log.error("Environment not specified. Please specify an environment variable.")
    else:
        env = sys.argv[1].lower()
        con, ds = get_snowflake_connection(env)
        classify_files(con, "VP_"+env.upper()+"SLDB", "DOC_AI", "LANDING_CLAIMS_TYPE")

if __name__ == '__main__':
    main()