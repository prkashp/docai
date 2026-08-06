import sys
from utils import get_snowflake_connection
import logging

logging.basicConfig(
    format='%(asctime)s %(levelname)-4s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
LIMIT = 800 #Pridiction limit is 1k but sometimes presigned url is timing out cross 3600 secs

def call_preprocessor_predict(con, database, schema, stage, table, build):
    '''
    This method calls predict function for the mentioned build on preprocessor custom trained model
    :param con: snowflake connection object
    :param database: VP Database name
    :param schema: Doc AI schema name
    :param stage: Landing stage name
    :param table: Claims Form Type table name
    :param build: preprocessor model build
    :return: int - number of records inserted
    '''
    try:
        con.cursor().execute(f"""ALTER STAGE {stage} REFRESH;""")
        results=con.cursor().execute(f'''
        INSERT INTO {database}.{schema}.{table}(MD5_HASH, JSON_CONTENT, LAST_MODIFIED, FILE_NAME, FILE_SIZE, FILE_URL)
        SELECT
            dir.MD5 AS MD5_HASH,
            PREPROCESSOR!PREDICT(GET_PRESIGNED_URL('@{stage}', RELATIVE_PATH), {build}) AS JSON_CONTENT, 
            dir.LAST_MODIFIED,
            dir.RELATIVE_PATH AS FILE_NAME,
            dir.SIZE AS FILE_SIZE,
            dir.FILE_URL
        FROM directory(@{stage}) dir
        LIMIT 800;
        ''')
    except Exception as error:
        log.error("Error while predicting results: " + error)
        sys.exit(1)
    else:
        if results.rowcount==0:
            log.warning("Preprocessor predict did not return any results. Please check s3 stage for files.")
        else:
            log.info(f"Preprocessor inserted {results.rowcount} records. Please check {schema}.{table}")
        return results.rowcount

def main():
    model_build_version = 3
    if len(sys.argv) <= 1:
        log.error("Environment not specified. Please specify an environment variable.")
    else:
        env = sys.argv[1].lower()
        con, ds = get_snowflake_connection(env)
        call_preprocessor_predict(con, "VP_"+env.upper()+"SLDB", "DOC_AI", env.upper()+"_ELDORADO_LANDING", "LANDING_CLAIMS_TYPE", model_build_version)


if __name__ == '__main__':
    main()