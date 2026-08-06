import logging
import boto3
import zipfile
from io import BytesIO
from datetime import datetime
import sys
from PIL import Image
from utils import get_s3_credentials

# configuring logger
logging.basicConfig(
    format='%(asctime)s %(levelname)-4s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
MAX_UNZIP_LIMIT=3  # Max 3 zips can be unzipped and moved to landing
MAX_MOVE_LIMIT=200 # Max 200 tif files can be moved at once reducing the DAG duration

def unzip_s3_file(env, subfolder, output_prefix, optimize=False):
    '''
    This method list the zip file, unzip it and archive the processed files
    Example:
    bucket_name: prod-enterprise-data-lake-refined
    subfolder: Eldorado_Vendor_Claims/
    output_prefix: Eldorado_Vendor_Claims_Refined/Landing
    :param bucket_name: S3 bucket name
    :param subfolder: Bucket keys where zip files are present
    :param output_prefix: Bucket key prefix where zip files will be extracted
    :param optimize: Optional step to optimize files by removing extra pages after 1st
    :return: Boolean
    '''
    global MAX_UNZIP_LIMIT
    global MAX_MOVE_LIMIT
    aws_access_key, aws_secret_key = get_s3_credentials(env)
    bucket_name = env+'-enterprise-data-lake-refined'
    s3 = boto3.client('s3',
                      region_name='us-east-1',
                      aws_access_key_id=aws_access_key,
                      aws_secret_access_key=aws_secret_key)

    # generating variables for dynamic s3 path creation
    now = datetime.now()
    year, month, day = now.strftime("%Y"), now.strftime("%m"), now.strftime("%d")
    content = {}
    upload_s3_path = ''
    try:
        # Download the zip file to memory
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=subfolder+'/Claims_') # get objects in claim prefix
        for content in response.get('Contents', []):
            if content['Key'][-4:]=='.zip':
                zip_object = s3.get_object(Bucket=bucket_name, Key=content['Key'])
                zip_content = zip_object['Body'].read()
                log.info("Reading "+content['Key'])
                # Extract files from the zip archive
                with zipfile.ZipFile(BytesIO(zip_content)) as zf:
                    for file_info in zf.infolist():
                        if not file_info.filename.endswith('/'):
                            upload_s3_path = '{output}/year={year}/month={month}/day={day}/{filename}'.format(
                                output=output_prefix,
                                year=year,
                                month=month,
                                day=day,
                                filename=file_info.filename)
                            if optimize:
                                modified_tiff_file = remove_pages_from_tiff(file_info.filename)
                                s3.upload_fileobj(
                                    modified_tiff_file,
                                    bucket_name,
                                    upload_s3_path,
                                    ExtraArgs={'ContentType': 'image/tif'}
                                )
                            else:
                                extracted_file = zf.open(file_info)
                                s3.upload_fileobj(
                                    extracted_file,
                                    bucket_name,
                                    upload_s3_path
                                )
                log.info("Moved extracted files to "+upload_s3_path+" for zip: "+content['Key'])
                # moving objects to archive
                s3.copy_object(Bucket=bucket_name, CopySource=bucket_name+'/'+content['Key'], Key=subfolder+'/archive/'+content['Key'].split('/',1)[-1])
                s3.delete_object(Bucket=bucket_name, Key=content['Key'])
                log.info("Archived zip file for "+content['Key'])
                MAX_UNZIP_LIMIT = MAX_UNZIP_LIMIT-1
                if MAX_UNZIP_LIMIT==0:
                    break
            elif content['Key'][-4:]=='.tif':
                destination = '{output}/year={year}/month={month}/day={day}/{filename}'.format(output=output_prefix,
                                                                                               year=year,
                                                                                               month=month,
                                                                                               day=day,
                                                                                               filename=content['Key'].split('/',2)[-1])
                if optimize:
                    file_obj = s3.get_object(Bucket=bucket_name, Key=content['Key'])
                    image_data = file_obj['Body'].read()
                    image_stream = BytesIO(image_data)
                    modified_tiff_file = remove_pages_from_tiff(image_stream)
                    s3.upload_fileobj(
                        modified_tiff_file,
                        bucket_name,
                        destination,
                        ExtraArgs={'ContentType': 'image/tif'}
                    )
                else:
                    s3.copy_object(Bucket=bucket_name, CopySource=bucket_name+'/'+content['Key'], Key=destination)
                log.info("Moved files to "+destination)
                s3.copy_object(Bucket=bucket_name, CopySource=bucket_name+'/'+content['Key'], Key=subfolder+'/archive/'+content['Key'].split('/',1)[-1])
                s3.delete_object(Bucket=bucket_name, Key=content['Key'])
                log.info("Archived file for "+content['Key'])

                MAX_MOVE_LIMIT = MAX_MOVE_LIMIT-1
                if MAX_MOVE_LIMIT==0:
                    break

        if MAX_UNZIP_LIMIT != 0 or MAX_MOVE_LIMIT != 0:
            log.warning(f"No new files found at {subfolder}.")
            return 1
        else:
            log.info(f"Files unzipped(or moved) at {output_prefix} and archived to {subfolder}/archive.")
            return 0

    except Exception as e:
        log.error(f"Error processing for {content}: {e}")
        sys.exit(1)


def remove_pages_from_tiff(input_path):
    """
    Removes pages from a TIFF file, starting from page 2 up to page 'n'.
    Args:
        input_path (object): Path to the input TIFF file.
    """
    try:
        with Image.open(input_path) as img:
            if img.n_frames < 1:
                log.info("No pages to remove as 'n' is less than or equal to 1.")
                return 0

            frames = []
            for i in range(img.n_frames):
                # log.info("Seeking through frame {}".format(i))
                img.seek(i)
                if i < 1: # Keep page 0
                    frames.append(img.copy())

            if frames:
                log.info(f"Pages removed from {input_path}")
                output_stream = BytesIO()
                frames[0].save(output_stream, format='TIFF')  # Specify the format explicitly
                output_stream.seek(0)
                return output_stream
            else:
                log.info(f"All pages after page 1 have been removed, resulting in no output.")
                return 0

    except FileNotFoundError:
        print(f"Error: Input file not found at {input_path}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)


def main():
    source = 'Eldorado_Vendor_Claims'
    destination = 'Eldorado_Vendor_Claims_Refined/Landing'
    env = sys.argv[1]
    unzip_s3_file(env, subfolder=source, output_prefix=destination, optimize=True)


if __name__ == '__main__':
    main()

