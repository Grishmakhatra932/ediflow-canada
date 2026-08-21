from pprint import pprint

from backend.app.edi.x12_parser import parse_purchase_order


file_path = "edi_samples/x12/valid_850.txt"
try:
    purchase_order = parse_purchase_order(file_path)
    pprint(purchase_order)

except ValueError as error:
    error_response = {
        "status": "rejected",
        "error": str(error),
    }

    pprint(error_response)