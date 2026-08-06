import sys
sys.path.append('/root/data-etl-pipelines/scripts/configs/')
import config
sys.path.append('/root/data-etl-pipelines/scripts/docai/eldorado/postprocessor/')
from datetime import date
from argparse import ArgumentParser
import subprocess

# usage:
# python postprocessor.py -env=qa
# The script is calling 2 scripts in sequence. The second one will run only when the first one is completed.

DEFAULT_ROOT_DIR="/root/data-etl-pipelines"
SCRIPT_DIR=f'/{DEFAULT_ROOT_DIR}/scripts/docai/eldorado/postprocessor/'
current_date = date.today().strftime("%Y%m%d")
log_file_path = "{DEFAULT_ROOT}/logs/{CURRENT_DATE}_task_master.log".format(DEFAULT_ROOT=DEFAULT_ROOT_DIR,CURRENT_DATE=current_date)
logger = config.console_and_file_logger("calling_calculate_score", log_file_path)

parser = ArgumentParser(description="Script for appending columns to import schema of snowflake databases")
parser.add_argument("-env", type=str, required=True, choices=['qa', 'stage', 'pilot', 'prod'] , help="Environment.")
args = parser.parse_args()


def main():
    logger.info(f"== {args.env.upper()} MASTER DOC AI postprocessing has started. ==")
    logger.info(f"==================================================================")

    try:
        # run validation to calculate score for every processed file
        subprocess.run(['python', f'{SCRIPT_DIR}calling_calculate_score.py'] + list([f'-env={args.env}']))
        # validate dental fees
        subprocess.run(['python', fr'{SCRIPT_DIR}/dental/validation.py'] + list([f' {args.env} landing_dental_claims']))
        # move file to the appropriate folder based on the result of the validation
        subprocess.run(['python', fr'{SCRIPT_DIR}calling_move_file.py'] + list([f'-env={args.env}']))

    except Exception as error:
        logger.error(error)
        sys.exit(1)

    logger.info(f"==================================================================")
    logger.info(f"== {args.env.upper()} MASTER DOC AI postprocessing has been completed. ==")

if __name__ == '__main__':
    main()