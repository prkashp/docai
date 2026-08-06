import sys
sys.path.append('/root/data-etl-pipelines/scripts/docai/eldorado/preprocessor/')
from utils import get_snowflake_connection, get_notification_parameters
sys.path.append('/root/data-etl-pipelines/scripts/configs/')
import config
from datetime import date
from argparse import ArgumentParser

# usage:
# python calculate_score.py -env=qa -claim_type=institutional

DEFAULT_ROOT_DIR="/root/data-etl-pipelines"
current_date = date.today().strftime("%Y%m%d")
log_file_path = "{DEFAULT_ROOT}/logs/{CURRENT_DATE}_calculate_score.log".format(DEFAULT_ROOT=DEFAULT_ROOT_DIR,CURRENT_DATE=current_date)
logger = config.console_and_file_logger("calculate_score", log_file_path)

parser = ArgumentParser(description="Script for appending columns to import schema of snowflake databases")
parser.add_argument("-env", type=str, required=True, choices=['qa', 'stage', 'pilot', 'prod'] , help="env.")
parser.add_argument("-claim_type", type=str, required=True, choices=['dental', 'institutional', 'professional'], help="Claim type.")
args = parser.parse_args()

INTEGRATION, RECIPIENTS = get_notification_parameters(f'{args.env.upper()}')

def calculate_score(Con, ClaimType):
    '''
For every table in schema DOC_AI which table_name contains ClaimType, this function calculates score of every file
inserted in table after the last score calculation.
The score of the file is calculated by procedure ADMIN.DOC_AI_VALIDATION(database_name, schema_name, table_name, claim_type).
The procedure calculate and insert score result in table ADMIN.DOC_AI_VALIDATION.
While inserting it checks score and if it is >0.98 the column passed_validation will be marked as true, otherwise as false.
The function does not return any values.
:param Con: snowflake connection object
:param ClaimType: claim type (dental, international, professional)
'''
    logger.info(f"== DOC AI {args.env.upper()} {ClaimType.upper()} validation for table has started. ==")

    try:
        sql=f"SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE UPPER(TABLE_SCHEMA)=UPPER('DOC_AI') AND TABLE_NAME ILIKE '%{ClaimType}%';"
        tables = Con.cursor().execute(f"{sql}")
        for table in tables:
            logger.info(f"== The validation for table {table[0].upper()} has started. ==")
            sql = f"CALL DOC_AI.DOC_AI_VALIDATION(CURRENT_DATABASE(), 'DOC_AI', '{table[0]}', '{ClaimType}');"
            logger.info(f"== Running procedure:{sql} ==")
            Con.cursor().execute(f"{sql}")
            logger.info(f"== DOC AI {ClaimType} validation for table {table[0]} has been completed successfully. ==")
    except Exception as error:
        logger.info(f"== DOC AI {args.env.upper()} {ClaimType.upper()} validation has failed. ==")
        logger.info(f"== Error: {error} ==")
        Con.cursor().execute(f"CALL SYSTEM$SEND_EMAIL('{INTEGRATION}','{RECIPIENTS}', '{ClaimType.upper()} {args.env.upper()} DOC AI postprocessing validation failed','ERROR: {error} \n Check the logs for the postprocessing validation for more details.');")
        sys.exit(1)

    logger.info(f"== DOC AI {args.env.upper()} {ClaimType.upper()} validation has been completed. ==\n")



def main():
    con, ds_name = get_snowflake_connection('{env}'.format(env=args.env.upper()))
    calculate_score(con, '{claim_type}'.format(claim_type=args.claim_type.upper()))


if __name__ == '__main__':
    main()