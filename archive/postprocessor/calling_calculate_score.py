import sys
sys.path.append('/root/data-etl-pipelines/scripts/configs/')
import config
sys.path.append('/root/data-etl-pipelines/scripts/docai/eldorado/postprocessor/')
from datetime import date
from argparse import ArgumentParser
import subprocess

# usage:
# python calling_calculate_score.py -env=qa
# The script is calling 3 scripts in parallel.
# They do not impact each other, but if one fail the whole process calling_calculate_score will not be marked completed successfully.

DEFAULT_ROOT_DIR="/root/data-etl-pipelines"
SCRIPT_DIR=f'{DEFAULT_ROOT_DIR}/scripts/docai/eldorado/postprocessor/'
current_date = date.today().strftime("%Y%m%d")
log_file_path = "{DEFAULT_ROOT}/logs/{CURRENT_DATE}_task_master.log".format(DEFAULT_ROOT=DEFAULT_ROOT_DIR,CURRENT_DATE=current_date)
logger = config.console_and_file_logger("calling_calculate_score", log_file_path)

parser = ArgumentParser(description="Script for appending columns to import schema of snowflake databases")
parser.add_argument("-env", type=str, required=True, choices=['qa', 'stage', 'pilot', 'prod'] , help="Environment.")
args = parser.parse_args()


def main():
    processes = []
    scripts = [
        [r'calculate_score.py',[f'-env={args.env}','-claim_type=dental']],
        [r'calculate_score.py',[f'-env={args.env}','-claim_type=institutional']],
        [r'calculate_score.py', [f'-env={args.env}','-claim_type=professional']]
]

    for script, arguments in scripts:
        p = subprocess.Popen(['python', SCRIPT_DIR+script] + list(arguments))
        processes.append(p)

    for p in processes:
        p.wait()


if __name__ == '__main__':
    main()