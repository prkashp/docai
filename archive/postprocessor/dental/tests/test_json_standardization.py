import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json_standardization

class TestTransformationFunctions(unittest.TestCase):

    def test_safe_get(self):
        d = {'a': 1}
        self.assertEqual(json_standardization.safe_get(d, 'a'), 1)
        self.assertEqual(json_standardization.safe_get(d, 'b', default='none'), 'none')
        self.assertEqual(json_standardization.safe_get(d, 'b'), '')

    def test_parse_patient_info(self):
        s = "Smith, John, 123 Main St, Springfield, IL 62704"
        result = json_standardization.parse_patient_info(s)
        expected = {
            "first": "John",
            "last": "Smith",
            "street": "123 Main St",
            "city": "Springfield",
            "state": "IL",
            "zip": "62704"
        }
        self.assertEqual(result, expected)

        # Test incomplete data
        s2 = "Lee"
        result2 = json_standardization.parse_patient_info(s2)
        expected2 = {
            "first": "",
            "last": "Lee",
            "street": "",
            "city": "",
            "state": "",
            "zip": ""
        }
        self.assertEqual(result2, expected2)

    def test_parse_policyholder_name(self):
        s_space = "John Smith"
        r_space = json_standardization.parse_policyholder_name(s_space)
        self.assertEqual(r_space, {"first": "John", "last": "Smith"})

        s_comma = "Smith, John"
        r_comma = json_standardization.parse_policyholder_name(s_comma)
        self.assertEqual(r_comma, {"last": "Smith", "first": "John"})

        s_empty = ""
        r_empty = json_standardization.parse_policyholder_name(s_empty)
        self.assertEqual(r_empty, {"first": "", "last": ""})

    def test_parse_organization_info(self):
        s = "DentalCare, 456 Elm St, Chicago, IL 60601"
        r = json_standardization.parse_organization_info(s)
        expected = {
            "name": "DentalCare",
            "street": "456 Elm St",
            "city": "Chicago",
            "state": "IL",
            "zip": "60601"
        }
        self.assertEqual(r, expected)

        # Test with less fields
        s2 = "Small Clinic"
        r2 = json_standardization.parse_organization_info(s2)
        expected2 = {
            "name": "Small Clinic",
            "street": "",
            "city": "",
            "state": "",
            "zip": ""
        }
        self.assertEqual(r2, expected2)

    def test_format_date(self):
        self.assertEqual(json_standardization.format_date("12/25/2022"), "20221225")
        self.assertEqual(json_standardization.format_date("02/01/2020"), "20200201")
        self.assertEqual(json_standardization.format_date("invalid date"), "")

    def test_get_relationship_code(self):
        self.assertEqual(json_standardization.get_relationship_code("spouse"), "01")
        self.assertEqual(json_standardization.get_relationship_code("child"), "19")
        self.assertEqual(json_standardization.get_relationship_code("self"), "18")
        self.assertEqual(json_standardization.get_relationship_code("other"), "G8")
        self.assertEqual(json_standardization.get_relationship_code("unknown"), "21")
        self.assertEqual(json_standardization.get_relationship_code("SPOUSE"), "01")  # case insensitive

    def test_parse_service_details(self):
        doc = {
            "PROCEDURECODE": '["D1110", "D2220"]',
            "FEE": '["100.0", "200.0"]'
        }
        services = json_standardization.parse_service_details(doc)
        self.assertEqual(len(services), 2)
        self.assertEqual(services[0]["service_line_number_LX"]["assigned_number_01"], 1)
        self.assertEqual(services[0]["dental_service_SV3"]["composite_medical_procedure_identifier_01"]["procedure_code_02"], "D1110")
        self.assertAlmostEqual(services[0]["dental_service_SV3"]["line_item_charge_amount_02"], 100.0)

        # Test with empty lists
        doc_empty = {
            "PROCEDURECODE": "[]",
            "FEE": "[]"
        }
        services_empty = json_standardization.parse_service_details(doc_empty)
        self.assertEqual(services_empty, [])

    def test_transform_document_basic(self):
        # Minimal doc input to avoid key errors
        doc = {
            "PATIENT_NAME": "Smith, John, 123 Main St, Springfield, IL 62704",
            "BILLPROVTIN": "12-3456789",
            "POLICYHOLDER_NAME": "John Smith",
            "DENTISTRY_DETAILS": "DentalCare, 456 Elm St, Chicago, IL 60601",
            "PATIENT_DOB": "01/01/1980",
            "PROCEDUREDATE": "[01/10/2021,01/20/2021]",
            "TOTAL_FEES": "123.45",
            "RELATIONSHIP": "self",
            "PROCEDURECODE": '["D1110","D1102"]',
            "FEE": '["100.5","22.95"]',
            "DENTAL_NPI": "1234567890",
            "POLICYHOLDER_SSN": "999-99-9999",
            "OTHERINS": "Insurance Co",
            "PATIENT_GENDER": "M",
            "PATIENT_ID": "P12345",
            "PLACEOFTREAT": "11",
            "RENDPROVID": "RP123",
            "RENDSPECIALTY": "SPE",
            "SERVPROVADD": "Smith"
        }
        result = json_standardization.transform_document(doc)
        self.assertIn("heading", result)
        self.assertIn("detail", result)
        self.assertEqual(result["heading"]["transaction_set_header_ST"]["transaction_set_identifier_code_01"], "837")
        self.assertEqual(result["detail"]["billing_provider_hierarchical_level_HL_loop"][0]["billing_provider_name_NM1_loop"]["billing_provider_name_NM1"]["billing_provider_identifier_09"], "1234567890")
        # self.assertEqual(result["transaction_set_trailer_SE"]["transaction_segment_count_01"], "33")
        # self.assertIsInstance(result["transaction_set_trailer_SE"]["transaction_set_control_number_02"], str)

        # Check services lines count
        services = result["detail"]["billing_provider_hierarchical_level_HL_loop"][0]["subscriber_hierarchical_level_HL_loop"][0]["patient_hierarchical_level_HL_loop"][0]["claim_information_CLM_loop"][0]["service_line_number_LX_loop"]
        self.assertEqual(len(services), 2)
        self.assertAlmostEqual(services[0]["dental_service_SV3"]["line_item_charge_amount_02"], 100.5)


if __name__ == "__main__":
    unittest.main()
