#!/bin/bash
#Ticket: ENG-81984
#Description: Script to get the EDI output from stedi.
#Author: Alok Nath Pandey

#usage:- 1. first run export stedi_api_key="stedi_api_key",
#        2.bash stedi_edi_export.sh
curl --request POST \
  --url https://core.us.stedi.com/2023-08-01/partnerships/local_PH_HC_TEST/transactions/005010X224A2-837 \
  --header "Authorization: $stedi_api_key" \
  --header 'Content-Type: application/json' \
  --data '{
  "filename": "my-output-file.edi",
  "transaction": {

  "heading": {
      "transaction_set_header_ST": {
        "transaction_set_identifier_code_01": "837",
        "transaction_set_control_number_02": 3456,
        "implementation_guide_version_name_03": "5010X224A2"
      },
      "beginning_of_hierarchical_transaction_BHT": {
        "hierarchical_structure_code_01": "0019",
        "transaction_set_purpose_code_02": "00",
        "originator_application_transaction_identifier_03": "14df18",
        "transaction_set_creation_date_04": "2025-07-17",
        "transaction_set_creation_time_05": "14:57",
        "claim_or_encounter_identifier_06": "CH"
      },
      "submitter_name_NM1_loop": {
        "submitter_name_NM1": {
          "entity_identifier_code_01": "41",
          "entity_type_qualifier_02": "2",
          "submitter_last_or_organization_name_03": "COMPANY NAME (INTERDENT EPO)",
          "identification_code_qualifier_08": "46",
          "submitter_identifier_09": "TGJ23"
        },
        "submitter_edi_contact_information_PER": [
          {
            "contact_function_code_01": "IC",
            "submitter_contact_name_02": "Nancy",
            "communication_number_qualifier_03": "TE",
            "communication_number_04": "7176149999"
          }
        ]
      },
      "receiver_name_NM1_loop": {
        "receiver_name_NM1": {
          "entity_identifier_code_01": "40",
          "entity_type_qualifier_02": "2",
          "receiver_name_03": "Healthcompp",
          "identification_code_qualifier_08": "46",
          "receiver_primary_identifier_09": "66783JJT"
        }
      }
    },
    "detail": {
      "billing_provider_hierarchical_level_HL_loop": [
        {
          "billing_provider_name_NM1_loop": {
            "billing_provider_name_NM1": {
              "entity_identifier_code_01": "85",
              "entity_type_qualifier_02": "2",
              "billing_provider_last_or_organizational_name_03": "COMPANY NAME (INTERDENT EPO)",
              "identification_code_qualifier_08": "XX",
              "billing_provider_identifier_09": "0123456789"
            },
            "billing_provider_address_N3": {
              "billing_provider_address_line_01": "PO Box 45018"
            },
            "billing_provider_city_state_zip_code_N4": {
              "billing_provider_city_name_01": "Fresno",
              "billing_provider_state_or_province_code_02": "CA",
              "billing_provider_postal_zone_or_zip_code_03": "93718"
            },
            "billing_provider_tax_identification_REF": {
              "reference_identification_qualifier_01": "EI",
              "billing_provider_tax_identification_number_02": "91-2009494"
            }
          },
          "subscriber_hierarchical_level_HL_loop": [
            {
              "subscriber_information_SBR": {
                "payer_responsibility_sequence_number_code_01": "P",
                "claim_filing_indicator_code_09": "CI"
              },
              "subscriber_name_NM1_loop": {
                "subscriber_name_NM1": {
                  "entity_identifier_code_01": "IL",
                  "entity_type_qualifier_02": "1",
                  "subscriber_last_name_03": "last",
                  "subscriber_first_name_04": "OTHER,NAME",
                  "identification_code_qualifier_08": "MI",
                  "subscriber_primary_identifier_09": "347764383"
                }
              },
              "payer_name_NM1_loop": {
                "payer_name_NM1": {
                  "entity_identifier_code_01": "PR",
                  "entity_type_qualifier_02": "2",
                  "payer_name_03": "Dental",
                  "identification_code_qualifier_08": "PI",
                  "payer_identifier_09": "null"
                }
              },
              "patient_hierarchical_level_HL_loop": [
                {
                  "patient_information_PAT": {
                    "individual_relationship_code_01": "19"
                  },
                  "patient_name_NM1_loop": {
                    "patient_name_NM1": {
                      "entity_identifier_code_01": "QC",
                      "entity_type_qualifier_02": "1",
                      "patient_last_name_03": "LAST",
                      "patient_first_name_04": "FIRST"
                    },
                    "patient_address_N3": {
                      "patient_address_line_01": "20429 Madeline st"
                    },
                    "patient_city_state_zip_code_N4": {
                      "patient_city_name_01": "Maricopa",
                      "patient_state_code_02": "AZ",
                      "patient_postal_zone_or_zip_code_03": "85138"
                    },
                    "patient_demographic_information_DMG": {
                      "date_time_period_format_qualifier_01": "D8",
                      "patient_birth_date_02": "09211974",
                      "patient_gender_code_03": "M"
                    }
                  },
                  "claim_information_CLM_loop": [
                    {
                      "claim_information_CLM": {
                        "patient_control_number_01": "12345678",
                        "total_claim_charge_amount_02": 576,
                        "health_care_service_location_information_05": {
                          "place_of_service_code_01": "11",
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
                        "service_date_03": "[04232025,04232025]"
                      },
                      "claim_identifier_for_transmission_intermediaries_REF": {
                        "reference_identification_qualifier_01": "D9",
                        "value_added_network_trace_number_02": "89961093182718758"
                      },
                      "rendering_provider_name_NM1_loop": {
                        "rendering_provider_name_NM1": {
                          "entity_identifier_code_01": "82",
                          "entity_type_qualifier_02": "1",
                          "rendering_provider_last_or_organization_name_03": "LAST",
                          "rendering_provider_first_name_04": "FIRST",
                          "identification_code_qualifier_08": "XX",
                          "rendering_provider_identifier_09": "1780754804"
                        },
                        "rendering_provider_specialty_information_PRV": {
                          "provider_code_01": "PE",
                          "reference_identification_qualifier_02": "PXC",
                          "provider_taxonomy_code_03": "1223S0112X"
                        }
                      },
                      "service_line_number_LX_loop": [
                        {
                          "service_line_number_LX": {
                            "assigned_number_01": 1
                          },
                          "dental_service_SV3": {
                            "composite_medical_procedure_identifier_01": {
                              "product_or_service_id_qualifier_01": "AD",
                              "procedure_code_02": "D0140"
                            },
                            "line_item_charge_amount_02": 155.0,
                            "procedure_count_06": 1
                          }
                        },
                        {
                          "service_line_number_LX": {
                            "assigned_number_01": 2
                          },
                          "dental_service_SV3": {
                            "composite_medical_procedure_identifier_01": {
                              "product_or_service_id_qualifier_01": "AD",
                              "procedure_code_02": "D7210"
                            },
                            "line_item_charge_amount_02": 421.0,
                            "procedure_count_06": 1
                          }
                        }
                      ]
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  },
    "summary": {
      "transaction_set_trailer_SE": {
        "number_of_included_segments_01": 4,
        "transaction_set_control_number_02": 1
      }
    }
  }
}'
