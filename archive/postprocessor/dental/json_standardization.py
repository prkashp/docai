import json
import uuid
import sys
import os
import re
from datetime import datetime

def get_environment_config(env_arg):
    """Returns configuration based on the environment argument."""
    return {
        "env": env_arg
    }

def safe_get(doc, key, default=""):
    """Safely gets a value from a dictionary, returning a default if not found."""
    return doc.get(key, default)

def parse_patient_info(patient_info_str):
    """Parses the patient information string into structured parts."""
    pat_parts = [p.strip() for p in patient_info_str.split(",")]
    # Use tuple unpacking with defaults for cleaner assignment
    pat_first, pat_last, pat_street, pat_city = "", "", "", ""
    pat_zipcode_parts = ["", ""]

    if len(pat_parts) > 0:
        pat_last = pat_parts[0]
    if len(pat_parts) > 1:
        pat_first = pat_parts[1]
    if len(pat_parts) > 2:
        pat_street = pat_parts[2]
    if len(pat_parts) > 3:
        pat_city = pat_parts[3]
    if len(pat_parts) > 4:
        pat_zipcode_parts = pat_parts[4].strip().split()

    pat_state = pat_zipcode_parts[0] if len(pat_zipcode_parts) > 0 else ""
    pat_zip = pat_zipcode_parts[1] if len(pat_zipcode_parts) > 1 else ""

    return {
        "first": pat_first,
        "last": pat_last,
        "street": pat_street,
        "city": pat_city,
        "state": pat_state,
        "zip": pat_zip
    }

def parse_policyholder_name(name_str):
    """Parses policyholder name into first and last, handling different delimiters."""
    name_str = name_str.strip()

    if ',' in name_str:
        parts = name_str.split(',', 1)  # Split only on the first comma
        last = parts[0].strip() if len(parts) > 0 else ""
        first = parts[1].strip() if len(parts) > 1 else ""
        return {"first": first, "last": last}
    elif ' ' in name_str:
        parts = name_str.split(' ', 1)  # Split only on the first space
        return {"first": parts[0].strip(), "last": parts[1].strip() if len(parts) > 1 else ""}
    elif name_str:
        # If there's no separator but non-empty name, treat whole as last name (or first, per business rule)
        return {"first": "", "last": name_str}
    else:
        return {"first": "", "last": ""}

def parse_policyholder_address(address_str):
    """Parses policyholder address into structured parts, handling different delimiters.
    
    Example inputs: 
    - "22331 N LINE ST, MARICOPA, AZ 85138"
    - "9929 E Ns, Apt 177, Fresno, California, 93720"
    
    Returns a dictionary with street, city, state, and zip components.
    """
    if not address_str or not isinstance(address_str, str):
        return {"street": "", "city": "", "state": "", "zip": ""}
    
    address_str = address_str.strip()
    
    # Handle common address formats with commas as delimiters
    parts = [part.strip() for part in address_str.split(',')]
    
    # Default values
    street = city = state = zip_code = ""
    
    # State abbreviation mapping (common states)
    state_mapping = {
        'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR', 'california': 'CA',
        'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE', 'florida': 'FL', 'georgia': 'GA',
        'hawaii': 'HI', 'idaho': 'ID', 'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA',
        'kansas': 'KS', 'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
        'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS', 'missouri': 'MO',
        'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV', 'new hampshire': 'NH', 'new jersey': 'NJ',
        'new mexico': 'NM', 'new york': 'NY', 'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH',
        'oklahoma': 'OK', 'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
        'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT', 'vermont': 'VT',
        'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV', 'wisconsin': 'WI', 'wyoming': 'WY'
    }
    
    # Check for apartment/suite in street address
    if len(parts) >= 2 and any(apt_indicator in parts[1].lower() for apt_indicator in ['apt', 'suite', 'unit', '#']):
        # Combine first two parts as street address
        street = f"{parts[0]}, {parts[1]}"
        # Shift remaining parts
        parts = [street] + parts[2:]
    else:
        # First part is street
        street = parts[0] if parts else ""
    
    # Process city, state, zip based on number of remaining parts
    if len(parts) >= 3:  # Street, City, State+Zip or Street, City, State, Zip
        city = parts[1]
        
        # Check if we have separate state and zip parts
        if len(parts) >= 4:  # Format: Street, City, State, Zip
            state_part = parts[2].lower()
            state = state_mapping.get(state_part, state_part.upper())
            zip_code = parts[3]
        else:  # Format: Street, City, State+Zip
            state_zip = parts[2].strip().split()
            if len(state_zip) >= 1:
                state_part = state_zip[0].lower()
                state = state_mapping.get(state_part, state_part.upper())
            if len(state_zip) >= 2:
                zip_code = state_zip[1]
            # Handle case where zip is the only item in the last part
            elif len(state_zip) == 1 and state_zip[0].isdigit():
                zip_code = state_zip[0]
                state = ""
    
    # Handle case where city, state, zip are in the same segment
    elif len(parts) == 2:
        city_state_zip = parts[1].split()
        if len(city_state_zip) >= 1:
            city = city_state_zip[0]
        if len(city_state_zip) >= 2:
            state_part = city_state_zip[1].lower()
            state = state_mapping.get(state_part, state_part.upper())
        if len(city_state_zip) >= 3:
            zip_code = city_state_zip[2]
    
    # Convert state to abbreviation if it's a full state name
    if state.lower() in state_mapping:
        state = state_mapping[state.lower()]
    
    # Ensure state is uppercase
    state = state.upper()
    
    return {
        "street": street,
        "city": city,
        "state": state,
        "zip": zip_code
    }

def parse_organization_info(org_info_str):
    """Parses organization information into structured parts."""
    org_parts = [p.strip() for p in org_info_str.split(",")]
    org_name = org_parts[0] if len(org_parts) > 0 else ""

    org_street = ""
    org_city = ""
    org_state = ""
    org_zip = ""

    if len(org_parts) > 1:
        # Assuming street is before city, state, zip and it's always at index -3 for fixed structure
        # This part of the original logic is a bit brittle, replicating it here.
        # A more robust solution might involve regex or more sophisticated parsing.
        org_street_city_state_zip = org_parts[1:]
        if len(org_street_city_state_zip) >= 3:
            org_street = org_street_city_state_zip[-3]
            org_city = org_street_city_state_zip[-2]
            org_state_zip = org_street_city_state_zip[-1].split()
            org_state = org_state_zip[0] if len(org_state_zip) > 0 else ""
            org_zip = org_state_zip[1] if len(org_state_zip) > 1 else ""

    return {
        "name": org_name,
        "street": org_street,
        "city": org_city,
        "state": org_state,
        "zip": org_zip
    }

def format_date(date_str, input_format="%m/%d/%Y", output_format="%Y%m%d"):
    """Formats a date string from one format to another."""
    try:
        return datetime.strptime(date_str, input_format).strftime(output_format)
    except ValueError as e:
        return f"Date format error: {e}" # Handle invalid date gracefully

def get_relationship_code(relationship_str):
    """Maps relationship string to a specific code."""
    rel_map = {
        'spouse': '01',
        'child': '19',
        'self': '18',
        'other': 'G8'
    }
    return rel_map.get(relationship_str.lower(), '21') # Default to '21'

def parse_service_details(doc):
    """Parses procedure codes and fees into a list of service dictionaries."""
    proc_code_str = safe_get(doc, "PROCEDURECODE", "").strip("[]")
    fees_str = safe_get(doc, "FEE", "").strip("[]")

    proc_codes = [p.strip().strip('"').strip("'") for p in proc_code_str.split(",") if p.strip()]
    fees = [f.strip().strip('"').strip("'") for f in fees_str.split(",") if f.strip()]

    # Ensure both lists have values, even if empty to prevent zip from errors
    # If one is shorter, zip will truncate to the shorter length, which is acceptable here.
    return [
        {
            "service_line_number_LX": {"assigned_number_01": i + 1},
            "dental_service_SV3": {
                "composite_medical_procedure_identifier_01": {
                    "product_or_service_id_qualifier_01": "AD",
                    "procedure_code_02": proc_code
                },
                "line_item_charge_amount_02": float(fee) if fee else None,
                "procedure_count_06": 1
            }
        }
        for i, (proc_code, fee) in enumerate(zip(proc_codes, fees))
    ]

# --- Main Data Transformation Function ---
def transform_document(doc):
    """Transforms a raw DocAI document into the desired output format."""

    # 1. Process Patient Information
    if safe_get(doc, "RELATIONSHIP", "").upper() == "SELF":
        patient_data = parse_policyholder_name(safe_get(doc, "POLICYHOLDER_NAME", ""))
    else:
        patient_data = parse_patient_info(safe_get(doc, "PATIENT_NAME", ""))


    # 2. Process Bill Provider TIN
    bill_provider_tin = re.sub(r'\D', '', safe_get(doc, "BILLPROVTIN")) #regex to only keep numbers

    # 3. Process Policyholder Information
    policyholder_data = parse_policyholder_name(safe_get(doc, "POLICYHOLDER_NAME", ""))
    policyholder_address_data = parse_policyholder_address(safe_get(doc, "POLICYHOLDER_ADDRESS", ""))

    # 4. Process Organization Information
    org_data = parse_organization_info(safe_get(doc, "DENTISTRY_DETAILS", ""))

    # 5. Process Dates
    dob = format_date(safe_get(doc, "PATIENT_DOB", ""))
    # Find max date from a comma-separated string of dates
    proc_dates_str = safe_get(doc, "PROCEDUREDATE", "").strip('[]')
    proc_dates = [format_date(dt.strip()) for dt in proc_dates_str.split(',') if dt.strip()]
    first_date = max(proc_dates) if proc_dates else "" # Max date, then format

    # 6. Process Total Charge
    total_charge = int(float(safe_get(doc, "TOTAL_FEES", "0")))

    # 7. Process Relationship Code
    relationship_code = get_relationship_code(safe_get(doc, "RELATIONSHIP"))

    # 8. Process Service Lines
    services = parse_service_details(doc)

    # 9. Construct the final output dictionary
    return {
        "heading": {
            "transaction_set_header_ST": {
                "transaction_set_identifier_code_01": "837",
                "transaction_set_control_number_02": 3456,
                "implementation_guide_version_name_03": "005010X224A2"
            },
            "beginning_of_hierarchical_transaction_BHT": {
                "hierarchical_structure_code_01": "0019",
                "transaction_set_purpose_code_02": "00",
                "originator_application_transaction_identifier_03": str(uuid.uuid4())[:6],
                "transaction_set_creation_date_04": datetime.now().strftime("%Y-%m-%d"),
                "transaction_set_creation_time_05": datetime.now().strftime("%H:%M"),
                "claim_or_encounter_identifier_06": "CH"
            },
            "submitter_name_NM1_loop": {
                "submitter_name_NM1": {
                    "entity_identifier_code_01": "41",
                    "entity_type_qualifier_02": "2",
                    "submitter_last_or_organization_name_03": 'DocAI',
                    "identification_code_qualifier_08": "46",
                    "submitter_identifier_09": "TGJ23"
                },
                "submitter_edi_contact_information_PER": [{
                    "contact_function_code_01": "IC",
                    "submitter_contact_name_02": "Nancy",
                    "communication_number_qualifier_03": "TE",
                    "communication_number_04": "7176149999"
                }]
            },
            "receiver_name_NM1_loop": {
                "receiver_name_NM1": {
                    "entity_identifier_code_01": "40",
                    "entity_type_qualifier_02": "2",
                    "receiver_name_03": "Healthcomp",
                    "identification_code_qualifier_08": "46",
                    "receiver_primary_identifier_09": "66783JJT"
                }
            }
        },
        "detail": {
                "billing_provider_hierarchical_level_HL_loop": [{
                "billing_provider_name_NM1_loop": {
                    "billing_provider_name_NM1": {
                        "entity_identifier_code_01": "85",
                        "entity_type_qualifier_02": "2",
                        "billing_provider_last_or_organizational_name_03": org_data["name"],
                        "identification_code_qualifier_08": "XX",
                        "billing_provider_identifier_09": safe_get(doc, "DENTAL_NPI") or None
                    },
                    "billing_provider_address_N3": {
                        "billing_provider_address_line_01": org_data["street"]
                    },
                    "billing_provider_city_state_zip_code_N4": {
                        "billing_provider_city_name_01": org_data["city"],
                        "billing_provider_state_or_province_code_02": org_data["state"],
                        "billing_provider_postal_zone_or_zip_code_03": org_data["zip"]
                    },
                    "billing_provider_tax_identification_REF": {
                        "reference_identification_qualifier_01": "EI",
                        "billing_provider_tax_identification_number_02": bill_provider_tin
                    }
                },
                "subscriber_hierarchical_level_HL_loop": [{
                    "subscriber_information_SBR": {
                        "payer_responsibility_sequence_number_code_01": "P",
                        "claim_filing_indicator_code_09": "CI"
                    },
                    "subscriber_name_NM1_loop": {
                        "subscriber_name_NM1": {
                            "entity_identifier_code_01": "IL",
                            "entity_type_qualifier_02": "1",
                            "subscriber_last_name_03": policyholder_data["last"],
                            "subscriber_first_name_04": policyholder_data["first"],
                            "identification_code_qualifier_08": "MI",
                            "subscriber_primary_identifier_09": safe_get(doc, "POLICYHOLDER_SSN") or None
                        },
                        "subscriber_address_N3": {
                            "subscriber_address_line_01": policyholder_address_data["street"]
                        },
                        "subscriber_city_state_zip_code_N4": {
                            "subscriber_city_name_01": policyholder_address_data["city"],
                            "subscriber_state_code_02": policyholder_address_data["state"],
                            "subscriber_postal_zone_or_zip_code_03": policyholder_address_data["zip"]
                        }
                    },
                    "payer_name_NM1_loop": {
                        "payer_name_NM1": {
                            "entity_identifier_code_01": "PR",
                            "entity_type_qualifier_02": "2",
                            "payer_name_03": safe_get(doc, "OTHERINS") or None,
                            "identification_code_qualifier_08": "PI",
                            "payer_identifier_09": "00"
                        }
                    },
                    "patient_hierarchical_level_HL_loop": [{
                        "patient_information_PAT": {
                            "individual_relationship_code_01": relationship_code
                        },
                        "patient_name_NM1_loop": {
                            "patient_name_NM1": {
                                "entity_identifier_code_01": "QC",
                                "entity_type_qualifier_02": "1",
                                "patient_last_name_03": patient_data["last"],
                                "patient_first_name_04": patient_data["first"]
                            },
                            "patient_address_N3": {
                                "patient_address_line_01": patient_data["street"]
                            },
                            "patient_city_state_zip_code_N4": {
                                "patient_city_name_01": patient_data["city"],
                                "patient_state_code_02": patient_data["state"],
                                "patient_postal_zone_or_zip_code_03": patient_data["zip"]
                            },
                            "patient_demographic_information_DMG": {
                                "date_time_period_format_qualifier_01": "D8",
                                "patient_birth_date_02": dob,
                                "patient_gender_code_03": safe_get(doc, "PATIENT_GENDER") or None
                            }
                        },
                        "claim_information_CLM_loop": [{
                            "claim_information_CLM": {
                                "patient_control_number_01": safe_get(doc, "PATIENT_ID") or None,
                                "total_claim_charge_amount_02": total_charge,
                                "health_care_service_location_information_05": {
                                    "place_of_service_code_01": safe_get(doc, "PLACEOFTREAT") or None,
                                    "facility_code_qualifier_02": "B",
                                    "claim_frequency_code_03": "1"
                                },
                                "provider_or_supplier_signature_indicator_06": "Y",
                                "assignment_or_plan_participation_code_07": "A",
                                "benefits_assignment_certification_indicator_08": "Y",
                                "release_of_information_code_09": "I"
                            },
                            "date_service_date_DTP": {
                                "date_time_qualifier_01": "472",
                                "date_time_period_format_qualifier_02": "D8",
                                "service_date_03": first_date
                            },
                            "claim_identifier_for_transmission_intermediaries_REF": {
                                "reference_identification_qualifier_01": "D9",
                                "value_added_network_trace_number_02": str(uuid.uuid4().int)[:17]
                            },
                            "rendering_provider_name_NM1_loop": {
                                "rendering_provider_name_NM1": {
                                    "entity_identifier_code_01": "82",
                                    "entity_type_qualifier_02": "1",
                                    "rendering_provider_last_or_organization_name_03": patient_data['last'], #treating dentist
                                    "rendering_provider_first_name_04": patient_data['first'], # treating dentist
                                    "identification_code_qualifier_08": "XX",
                                    "rendering_provider_identifier_09": safe_get(doc, "RENDPROVID") or None
                                },
                                "rendering_provider_specialty_information_PRV": {
                                    "provider_code_01": "PE",
                                    "reference_identification_qualifier_02": "PXC",
                                    "provider_taxonomy_code_03": safe_get(doc, "RENDSPECIALTY") or None
                                }
                            },
                            "service_line_number_LX_loop": services
                        }]
                    }]
                }]
            }]
        }
    }

# --- Main execution flow (imperative but uses functional components) ---

def main():
    try:
        with open('../20250521000606920001_0_0_0.json', 'r') as f:
            mocked_doc = json.load(f)
    except FileNotFoundError:
        print("Error: Mocked_docai.json not found. Please ensure it's in the same directory.")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Error: Could not decode JSON from Mocked_docai.json.")
        sys.exit(1)

    # Perform the transformation
    output_data = transform_document(mocked_doc)

    # Print the output
    print(json.dumps(output_data, indent=2))



if __name__ == "__main__":
    main()
