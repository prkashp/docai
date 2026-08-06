import json
import os
import sys
import snowflake.connector
import logging

logging.basicConfig(
    format='%(asctime)s %(levelname)-4s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def decrypt_password(enc_password, salt, secret_key):
    """
    Function for decrypting credentials with encryption-util.py script.
    :param enc_password: Encrypted password
    :param salt: SALT used for decrypting the password
    :param secret_key: Secret key used for decrypting the password. ({ENV}_MATRIX_SECRET_KEY)
    :return Password: Returns a string as decrypted password
    """
    import subprocess
    encrypt_util_script = '/root/data-etl-pipelines/scripts/utils/encryption-util.py'
    return subprocess.check_output("{script} \
                                    --text={text} \
                                    --salt={salt} \
                                    --secret={secret} \
                                    --decrypt=True".format(script=encrypt_util_script,
                                                           text=enc_password,
                                                           salt=salt,
                                                           secret=os.environ[secret_key]
                                                           ),
                                   shell=True
                                   ).splitlines()[0].decode()

def get_s3_credentials(env):
    """
    Function for getting necessary credentials from config file and decrypts them using decrypt_password() function.
    :param data_source: json file with encrypted credentials
    :return aws_access_key, aws_secret_key: Returns credentials need for the script
    """
    # path to credentials config file
    data_source = "/root/data-etl-pipelines/scripts/configs/data_source_json/{env}_data_source.json".format(env=env.lower())

    with open(data_source, 'r') as cred_dict:
        creds = json.load(cred_dict)
    aws_access_key = creds['s3']['aws_access_key']
    aws_secret_key = decrypt_password(creds['s3']["aws_secret_key"], creds['configs']["salt"],creds['configs']["secret_key"])
    return aws_access_key, aws_secret_key

def get_snowflake_connection(env):
    """
    Gets Snowflake Connection
    """
    DEFAULT_ROOT_DIR='/root/data-etl-pipelines'
    CONFIG_LOCATION = '{DEFAULT_ROOT}/scripts/configs/data_source_json/{env}_data_source.json'.format(DEFAULT_ROOT=DEFAULT_ROOT_DIR,env=env.lower())

    try:
        with open(CONFIG_LOCATION, 'r') as fp:
            config_params = json.load(fp)
            sf_connection_params = config_params['snowflake_docai'] # using docai specific role
            con = snowflake.connector.connect(user=sf_connection_params["user_name"],
                                              private_key=decrypt_password(sf_connection_params["private_key"],config_params["configs"]["salt"],config_params["configs"]["secret_key"]),
                                              account=sf_connection_params["account"],
                                              database=sf_connection_params["dsname"],
                                              schema=sf_connection_params["schema"],
                                              warehouse=sf_connection_params["warehouse"],
                                              role=sf_connection_params["user_role"]
                                              )
        log.info("=== Connection to Snowflake was successful ===")
    except Exception as e:
        log.error(f"Error processing for: {e}")
        sys.exit(1)
    return con, sf_connection_params['dsname']

def get_notification_parameters(env):
    """
    :param env:
    :return: notification integration and email recipients
    """
    # path to credentials config file
    data_source = "/root/data-etl-pipelines/scripts/configs/data_source_json/{env}_data_source.json".format(env=env.lower())


    with open(data_source, 'r') as cred_dict:
        creds = json.load(cred_dict)
    notification_integration = creds['configs']['notification_integration']
    email_recipients = creds['configs']['notification_integration_email_recipients']
    return notification_integration, email_recipients

def main():
    print(get_s3_credentials(sys.argv[1]))
    print(get_snowflake_connection(sys.argv[1]))
if __name__ == '__main__':
    main()