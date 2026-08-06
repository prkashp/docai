import sys
import logging
sys.path.append('/root/data-etl-pipelines/scripts/docai/eldorado/preprocessor/')
from utils import get_snowflake_connection, get_notification_parameters
sys.path.append('/root/data-etl-pipelines/scripts/configs/')


# usage:
# args[1]: environment
# args[2]: claim type tables. Eg.landing_dental_claims
# python validation.py prod landing_dental_claims

DEFAULT_ROOT_DIR="/root/data-etl-pipelines"
# configuring logger
logging.basicConfig(
    format='%(asctime)s %(levelname)-4s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def dollar_amount_validation(con, table, line_item, total):
    """
    :param con:
    :param table:
    :param line_item:
    :param total:
    :return:
    """
    # Regex to remove bad characters for dollar amount
    regex = '[(a-z)(A-Z)($,:;% )]'
    email_text = '''
    <!DOCTYPE html>
    <html>
    <head>
    <style>
    table, th, td {
      border: 1px solid black;
    }
    </style>
    </head>
    <body>
    <h1>Fees Mismatch list</h1>
    <table>
      <tr>
        <th>relativePath</th>
        <th>ocr</th>
        <th>calcFee</th>
        <th>totalFee</th>
        <th>rawFee</th>
        <th>rawTotalFee</th>
      </tr>
    '''
    try:
        results=con.cursor().execute(f'''
        SELECT  FILE_NAME, 
                JSON_CONTENT:"__documentMetadata":"ocrScore" as OCR,
                JSON_CONTENT:"Fee" as FEE_JSON,
                JSON_CONTENT:"TOTAL_FEES" as TOTAL_FEES_JSON,
                REDUCE(FEE
                        ,0
                        ,(acc,val) -> acc+TRY_TO_DECIMAL(val::VARCHAR)) AS CALCULATED_FEE
                ,TRY_TO_DECIMAL(TOTAL_FEE::VARCHAR) AS TOTAL_FEE
        FROM (
            SELECT FILE_NAME,
                   JSON_CONTENT,
                   TRANSFORM(JSON_CONTENT:"{line_item}", fee -> REGEXP_REPLACE(fee:"value",'[(a-z)(A-Z)($,:;% )]','')) AS FEE,
                   REGEXP_REPLACE(JSON_CONTENT:"{total}"[0]:"value",'[(a-z)(A-Z)($,:;% )]','') AS TOTAL_FEE
            FROM {table}
            WHERE JSON_CONTENT:"{line_item}" IS NOT NULL AND JSON_CONTENT:"{total}" IS NOT NULL
            )
        WHERE CALCULATED_FEE!=TRY_TO_DECIMAL(TOTAL_FEE::VARCHAR);
        ''')
        log.info(f"Fetched results from {table}: {results.rowcount}")
    except Exception as error:
        log.error("Error getting file path results: " + str(error))
        sys.exit(1)
    else:
        for record in results.fetchall():
            email_text+='''
              <tr>
                '''
            email_text+=('<td>'+str(record[0])+'</td>'
                         +'<td>'+str(record[1])+'</td>'
                         +'<td>'+str(record[2])+'</td>'
                         +'<td>'+str(record[3])+'</td>'
                         +'<td>'+str(record[4])+'</td>'
                         +'<td>'+str(record[5])+'</td>')
            email_text+='''
                </tr>
                '''
        email_text+='''
        </table>
        </body>
        </html>
        '''
        try:

            integration, recipients = get_notification_parameters(f'{sys.argv[1].upper()}')
            con.cursor().execute(f"""CALL SYSTEM$SEND_EMAIL('{integration}', '{recipients}', 'DOC AI Dental Validation: Total Fees (check outlook email for full report)','{email_text}','text/html');""")
        except Exception as error:
            log.error("Error sending email: " + str(error))
            sys.exit(1)

def main():
    con, ds_name = get_snowflake_connection('{env}'.format(env=sys.argv[1].upper()))
    dollar_amount_validation(con = con, table = sys.argv[2], line_item = 'Fee', total = 'TOTAL_FEES')

if __name__ == '__main__':
    main()