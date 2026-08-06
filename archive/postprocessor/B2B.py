import boto3
import json
from datetime import datetime
import uuid
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../preprocessor')))
from utils import get_s3_credentials

# --s3 config--
env=sys.argv[1]
key, secrets = get_s3_credentials(env)
s3 = boto3.client("s3",
                  aws_access_key_id=key,
                  aws_secret_access_key=secrets)

input_bucket = f"{env}-enterprise-data-lake-refined"
input_folder = "Eldorado_Vendor_Claims/Files_for conversion/B2B_Input/"
output_bucket = f"{env}-enterprise-data-lake-refined"
output_folder = "Eldorado_Vendor_Claims/Files_for conversion/B2B_Output/"

# --Helper function--

def get_val(doc, key):
    return doc.get(key, "")

def format_date(date_str):
    if not date_str:
        return None
    date_str=date_str.strip()
    for fmt in ("%m-%d-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str,fmt).strftime("%Y%m%d")
        except ValueError:
            continue
    print(f"error date format: {date_str}")
    return None


def split_name(name):
    if name and "," in name:
        last, rest = name.split(",", 1)
        return last.strip(), rest.strip().split()[0]


def parse_address(addr):
    parts = addr.strip().split()
    return " ".join(parts[:-3]), parts[-3], parts[-2], parts[-1]

def parse_array(val):
    if isinstance(val, str):
        val = val.strip("[]")
        items = [v.strip(" []") for v in val.split(",") if v.strip()]
        return items
    elif isinstance(val,list):
        return val
    elif val:
        return [str(val)]
    return []

# --process files from s3--
response = s3.list_objects_v2(Bucket=input_bucket, Prefix=input_folder)
files = [obj["Key"] for obj in response.get("Contents", []) if obj["Key"].endswith(".json")]
for i, key in enumerate(files):
    obj = s3.get_object(Bucket=input_bucket, Key=key)
    doc = json.loads(obj["Body"].read().decode("utf-8"))
    # Parse inputs
    proc_codes = parse_array(get_val(doc, "PROCEDURECODE"))
    proc_dates = parse_array(get_val(doc, "PROCEDUREDATE"))
    fees = parse_array(get_val(doc, "FEE"))
    total_charge = str(get_val(doc, "TOTAL_FEES"))
    print("code",proc_codes)
    print("date",proc_dates)
    print("fee", fees)
#validation logic
    if not (len(proc_codes) == len(proc_dates)==len(fees)):
        print(f"Skipping file {key} due to mismatch fields values")
        continue
    # Build services[]

    services = []
    for idx in range(len(fees)):
        code = proc_codes[idx]
        fee = str(fees[idx])
        date = format_date(proc_dates[idx])
        services.append({
            "lineNumber": str(idx + 1),
            "procedure": {
                "qualifier": "AD",
                "code": code,
                "modifier": "P",
                "chargeAmount": fee,
                "placeOfService": get_val(doc, "PLACEOFTREAT"),
                "quantity": "1"
            },

            "serviceDate": {
                "qualifier": "472",
                "format": "D8",
                "date": date
            }

        })

    # Static data

    org_parts = get_val(doc, "COMPANY_DETAILS").split()
    org_name = " ".join(org_parts[0:2])
    org_street = " ".join(org_parts[2:-3])
    org_city, org_state, org_zip = org_parts[-3].replace(",", ""), org_parts[-2], org_parts[-1]
    sub_last, sub_first = split_name(get_val(doc, "POLICYHOLDER_NAME"))
    _, sub_city, sub_state, sub_zip = parse_address(get_val(doc, "POLICYHOLDER_ADDRESS"))
    pat_last, pat_first = split_name(get_val(doc, "PATIENT_NAME"))
    pat_street = org_street
    pat_city, pat_state, pat_zip = org_city, org_state, org_zip
    dob = format_date(get_val(doc, "PATIENT_DOB"))
    control_num = str(uuid.uuid4())[:8]
    first_date = format_date(proc_dates[0]) if proc_dates else "19000101"

    # Build output JSON

    output = {
        "transactionInfo": {
            "type": "837D",
            "controlNumber": control_num,
            "version": "005010X224A2"
        },

        "billingProvider": {
            "organizationName": org_name,
            "address": {
                "street": org_street,
                "city": org_city,
                "state": org_state,
                "zip": org_zip
            },

            "taxId": {
                "type": "EI",
                "value": get_val(doc, "DENTAL_SSN")
            }
        },

        "subscriber": {
            "hierarchicalLevel": {
                "id": "2",
                "parentId": "1",
                "levelCode": "22",
                "childCode": "1"
            },
            "information": {
                "payerResponsibility": "P",
                "insuranceType": "ZZ"
            },
            "name": {
                "entityType": "IL",
                "entityTypeQualifier": "1",
                "lastName": sub_last,
                "firstName": sub_first,
                "idQualifier": "MI",
                "id": get_val(doc, "POLICYHOLDER_SSN")
            },

            "address": {
                "city": sub_city,
                "state": sub_state,
                "zip": sub_zip
            }
        },

        "patient": {
            "hierarchicalLevel": {
                "id": "3",
                "parentId": "2",
                "levelCode": "23",
                "childCode": "0"
            },

            "relationship": "18",
            "name": {
                "entityType": "QC",
                "entityTypeQualifier": "1",
                "lastName": pat_last,
                "firstName": pat_first
            },

            "address": {
                "street": pat_street,
                "city": pat_city,
                "state": pat_state,
                "zip": pat_zip
            },

            "demographics": {
                "qualifier": "D8",
                "dateOfBirth": dob,
                "gender": get_val(doc, "PATIENT_GENDER")
            }

        },

        "claim": {
            "claimNumber": get_val(doc, "PATIENT_ID"),
            "chargeAmount": total_charge,
            "placeOfService": get_val(doc, "PLACEOFTREAT"),
            "type": "B",
            "frequency": "1",
            "signatureIndicator": "Y",
            "assignmentCode": "C",
            "benefitsAssignmentCertification": "Y",
            "releaseInfoCode": "I",
            "serviceDate": {
                "qualifier": "472",
                "format": "RD8",
                "period": f"{first_date}-{first_date}"
            },

            "attachmentReference": {
                "qualifier": "F8",
                "value": f"{get_val(doc, 'PATIENT_ID')}.tif"
            }
        },

        "renderingProvider": {
            "name": {
                "entityType": "82",
                "entityTypeQualifier": "1",
                "lastName": pat_last,
                "firstName": pat_first,
                "middleName": "",
                "idQualifier": "XX",
                "npi": get_val(doc, "DENTAL_NPI")

            },

            "specialty": {
                "code": "PE",
                "taxonomyQualifier": "PXC",
                "taxonomyCode": "1223G0001X"
            },

            "organization": {
                "name": org_name,
                "address": {
                    "street": org_street,
                    "city": org_city,
                    "state": org_state,
                    "zip": org_zip
                }
            }
        },
        "services": services,
        "trailer": {
            "segmentCount": "33",
            "controlNumber": control_num,
            "functionalGroupCount": "1",
            "interchangeControlNumber": "000012148"
        }
    }

    # Save output file to S3
    output_key = f"{output_folder}{i + 1}.json"
    s3.put_object(
        Bucket=output_bucket,
        Key=output_key,
        Body=json.dumps(output, indent=2).encode("utf-8")
    )

print(f"Output {len(files)} files and saved to {output_bucket}/{output_folder}N.json format")
