import sys
import logging
sys.path.append('/root/data-etl-pipelines/scripts/docai/eldorado/preprocessor/')
from utils import get_snowflake_connection

logging.basicConfig(
    format='%(asctime)s %(levelname)-4s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

def call_professional_predict(con, database, schema, stage, table, build):
    '''
    This method calls predict function for the mentioned build on professional health claim custom trained model
    :param con: snowflake connection object
    :param database: VP Database name
    :param schema: Doc AI schema name
    :param stage: Landing stage name
    :param table: Claims Form Type table name
    :param build: professional health claim 1 model build
    :return: int - number of records inserted
    '''
    try:
        con.cursor().execute(f"""ALTER STAGE {stage} REFRESH;""")
        log.info(f"Refreshed {stage} stage")
        results=con.cursor().execute(f"""
        INSERT INTO {database}.{schema}.{table}(MD5_HASH, JSON_CONTENT, LAST_MODIFIED, FILE_NAME, FILE_SIZE, FILE_URL)
        SELECT
            MD5 AS MD5_HASH,
            PROFESSIONAL_HEALTH_CLAIMS!PREDICT(GET_PRESIGNED_URL('@{stage}', RELATIVE_PATH), {build}) AS JSON_CONTENT,
            LAST_MODIFIED,
            RELATIVE_PATH AS FILE_NAME,
            SIZE AS FILE_SIZE,
            FILE_URL
        FROM directory(@{stage}) dir
        WHERE MD5_HASH NOT IN (SELECT MD5_HASH FROM {database}.{schema}.{table})
        LIMIT 200;
        """)
    except Exception as error:
        log.error("Error while predicting results: " + error)
        sys.exit(1)
    else:
        if results.rowcount==0:
            log.warning("Professional health claim predict did not return any results. Please check s3 stage for files.")
            delete_bad_predicts=con.cursor().execute(f"""
                DELETE FROM {database}.{schema}.{table} 
                WHERE JSON_CONTENT:"__processingErrors"[0]::VARCHAR='Received HTTP 403 response for presigned URL. URL may be expired.';
                """)
            if delete_bad_predicts.fetchone()[0]>0:
                log.warning(f"Total of {delete_bad_predicts.fetchone()[0]} docs weren't processed correctly and would be picked up on next run.")
        else:
            log.info(f"Professional health claim inserted {results.rowcount} records. Please check {schema}.{table}")
        return results.rowcount

def main():
    model_build_version = 5
    if len(sys.argv) <= 1:
        log.error("Environment not specified. Please specify an environment variable.")
    else:
        env = sys.argv[1].lower()
        con, ds = get_snowflake_connection(env)
        call_professional_predict(con, "VP_"+env.upper()+"SLDB", "DOC_AI", env.upper()+"_ELDORADO_PROFESSIONAL", "LANDING_PROFESSIONAL_CLAIMS", model_build_version)


if __name__ == '__main__':
    main()