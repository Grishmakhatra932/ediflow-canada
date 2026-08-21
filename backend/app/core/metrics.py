from prometheus_client import Counter


api_requests_total = Counter(
    "ediflow_api_requests_total",
    "Total number of API requests processed",
)

edi_completed_total = Counter(
    "ediflow_edi_completed_total",
    "Total number of successfully completed EDI transactions",
)

edi_rejected_total = Counter(
    "ediflow_edi_rejected_total",
    "Total number of rejected EDI transactions",
)

edi_failed_total = Counter(
    "ediflow_edi_failed_total",
    "Total number of failed EDI transactions",
)