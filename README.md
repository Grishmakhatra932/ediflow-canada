# EDIFlow Canada

A production-style **EDI integration and observability platform** built with FastAPI, PostgreSQL, Docker, Prometheus, and Grafana.

EDIFlow Canada processes **ANSI X12 850 Purchase Orders**, validates incoming transactions, detects duplicates, simulates ERP integration, handles retry and failure scenarios, stores transaction audit records, and exposes operational metrics for monitoring.

---

## Architecture

![EDIFlow Canada Architecture](docs/images/ediflow-architecture.png)

---

## Key Features

- ANSI X12 850 Purchase Order processing
- ISA, BEG, N1, and PO1 segment parsing
- Purchase order and item-level validation
- API-key protected EDI upload endpoint
- Duplicate detection using EDI control number and purchase order number
- Mock ERP purchase order integration
- Configurable ERP failure simulation
- Automatic ERP retry logic
- PostgreSQL transaction persistence
- Alembic database migrations
- Structured application logging
- REST APIs using FastAPI
- Docker Compose containerization
- Prometheus metrics collection
- Grafana monitoring dashboard
- Automated API and integration testing

---

## Technology Stack

| Category | Technologies |
|---|---|
| Backend | Python, FastAPI |
| EDI | ANSI X12 850 |
| Database | PostgreSQL, SQLAlchemy |
| Database Migration | Alembic |
| Testing | Pytest, HTTPX |
| Security | API Key Authentication |
| Containerization | Docker, Docker Compose |
| Monitoring | Prometheus |
| Visualization | Grafana |
| API Documentation | Swagger / OpenAPI |
| Version Control | Git, GitHub |

---

## EDI Processing Workflow

```text
Trading Partner / Customer
          |
          | X12 850 Purchase Order
          v
    FastAPI Upload API
          |
          v
   API Key Authentication
          |
          v
      X12 Parser
          |
          v
      Validation
          |
     +----+----+
     |         |
 Invalid     Valid
     |         |
     v         v
 Rejected   Duplicate Detection
                  |
             +----+----+
             |         |
         Duplicate   Unique
             |         |
             v         v
          Rejected   ERP Integration
                         |
                    Retry / Failure
                       Logic
                    +----+----+
                    |         |
                 Success    Failure
                    |         |
                    v         v
                Completed   Failed
                    \         /
                     \       /
                      \     /
                     PostgreSQL
                  Transaction Audit
                        |
                        v
                    Prometheus
                        |
                        v
                      Grafana
```

---

## Transaction States

EDIFlow tracks three primary transaction outcomes.

### Completed

The X12 transaction passes validation and duplicate checks, is processed through the ERP integration layer, and receives an ERP order number.

### Rejected

The transaction is rejected before ERP processing because of data or validation problems such as:

- Missing required EDI segments
- Invalid quantities
- Invalid prices
- Missing buyer information
- Missing supplier information
- Missing SKU or unit information
- Duplicate control numbers
- Duplicate purchase order numbers

### Failed

The transaction passes EDI validation but the downstream ERP integration fails after retry attempts.

---

## Monitoring Dashboard

EDIFlow exposes Prometheus metrics that are visualized through Grafana.

![Grafana Transaction Monitoring](docs/images/grafana-dashboard.png)

The dashboard monitors:

- Completed EDI transactions
- Rejected EDI transactions
- Failed EDI transactions

Current custom metrics include:

```text
ediflow_edi_completed_total
ediflow_edi_rejected_total
ediflow_edi_failed_total
ediflow_api_requests_total
```

---

## Prometheus Target Health

Prometheus continuously scrapes metrics from the FastAPI application.

![Prometheus Target Health](docs/images/prometheus-target.png)

FastAPI exposes Prometheus-compatible metrics through:

```text
GET /metrics
```

The monitoring stack runs inside Docker Compose and Prometheus communicates with the API service through the Docker network.

---

## PostgreSQL Transaction Audit

Every processed EDI transaction is stored for operational traceability and troubleshooting.

![EDI Transaction History](docs/images/transaction-history.png)

Transaction audit records include fields such as:

```text
id
filename
status
control_number
purchase_order_number
erp_order_number
error_message
created_at
```

The audit trail allows completed, rejected, and failed transactions to be reviewed through the transaction history API.

---

## Main API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Application information |
| GET | `/health` | Service health check |
| POST | `/api/edi/upload` | Upload and process an X12 850 file |
| GET | `/api/edi/sample` | Parse a sample EDI transaction |
| GET | `/api/transactions` | Retrieve transaction audit history |
| GET | `/metrics` | Expose Prometheus metrics |
| GET | `/api/erp/simulation-mode` | View current ERP simulation mode |
| POST | `/api/erp/simulation-mode/{mode}` | Change ERP simulation behavior |

---

## ERP Failure Simulation

The project contains a mock ERP integration layer that can simulate multiple downstream behaviors.

### Normal Mode

```text
none
```

The ERP integration processes the purchase order successfully.

### Retry Mode

```text
retry
```

The ERP integration temporarily fails and succeeds after retry attempts.

### Permanent Failure Mode

```text
permanent
```

The ERP integration continuously fails, resulting in a failed EDI transaction.

This simulation makes it possible to demonstrate retry handling, downstream service failures, error persistence, and monitoring without requiring access to a commercial ERP system.

---

## Example ANSI X12 850

```text
ISA*00*          *00*          *ZZ*MAPLERETAIL    *ZZ*NORTHSTAR     *260822*1300*U*00401*000001105*0*T*>~
GS*PO*MAPLERETAIL*NORTHSTAR*20260822*1300*1*X*004010~
ST*850*0001~
BEG*00*NE*PO-COMPLETE-005**20260822~
REF*DP*001~
N1*BY*Maple Retail Canada*92*BUYER001~
N1*SU*NorthStar Foods*92*SUP1001~
PO1*1*50*CA*6.25**SK*SKU-9105~
CTT*1~
SE*8*0001~
GE*1*1~
IEA*1*000001105~
```

Important segments processed by the application include:

| Segment | Purpose |
|---|---|
| ISA | Interchange control information |
| GS | Functional group information |
| ST | Transaction set header |
| BEG | Purchase order header |
| N1 | Buyer and supplier information |
| PO1 | Purchase order line items |
| CTT | Transaction totals |
| SE | Transaction set trailer |
| GE | Functional group trailer |
| IEA | Interchange control trailer |

---

## Validation

The EDI parser and validator check for common integration problems before sending data to the ERP layer.

Examples include:

- Missing ISA segment
- Incomplete ISA segment
- Missing EDI control number
- Missing BEG segment
- Missing purchase order number
- Missing or invalid order date
- Missing buyer
- Missing supplier
- Missing PO1 items
- Invalid quantity
- Negative unit price
- Invalid numeric values
- Missing item SKU
- Missing item unit
- Unsupported file extension
- Invalid file encoding

This helps prevent malformed transactions from reaching downstream systems.

---

## Duplicate Detection

EDIFlow prevents duplicate transaction processing using two important business identifiers:

```text
EDI Control Number
Purchase Order Number
```

If either identifier has already been processed, the application rejects the duplicate transaction.

Database uniqueness constraints provide an additional level of protection against duplicate records.

---

## ERP Integration Flow

After the X12 850 transaction is parsed and validated, the application maps it into an ERP-compatible purchase order structure.

Example mapped fields include:

```text
purchase_order_number
order_date
currency
buyer
supplier
items
```

Each line item contains:

```text
line_number
sku
quantity
unit
unit_price
```

The mock ERP service then returns an ERP order number when processing succeeds.

Example:

```text
ERP-PO-COMPLETE-005
```

---

## Retry Handling

The ERP integration layer includes retry behavior for temporary downstream failures.

In retry simulation mode:

```text
Attempt 1 -> Failed
Attempt 2 -> Failed
Attempt 3 -> Success
```

If the ERP service continues to fail, the transaction is recorded with:

```text
status = failed
```

and the corresponding error information is stored in PostgreSQL.

---

## API Security

The EDI upload endpoint is protected using API key authentication.

The request must include:

```text
X-API-Key
```

Requests with a missing or invalid API key receive:

```text
401 Unauthorized
```

Real API credentials are stored in environment variables and are not committed to the Git repository.

---

## Running the Project

### 1. Clone the Repository

```bash
git clone https://github.com/Grishmakhatra932/ediflow-canada.git
cd ediflow-canada
```

### 2. Create Environment Configuration

Create a `.env` file based on `.env.example`.

Example:

```env
DATABASE_URL=postgresql+psycopg://postgres:your-password@localhost:5432/ediflow
API_KEY=your-api-key-here

POSTGRES_DB=ediflow
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

DOCKER_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/ediflow

ERP_FAILURE_MODE=none
```

Never commit the real `.env` file or real credentials.

### 3. Build and Start the Platform

```bash
docker compose up -d --build
```

### 4. Verify Running Containers

```bash
docker compose ps
```

The stack includes:

```text
FastAPI
PostgreSQL
Prometheus
Grafana
```

---

## Application URLs

After starting Docker Compose:

| Service | URL |
|---|---|
| Swagger API | http://localhost:8000/docs |
| FastAPI Metrics | http://localhost:8000/metrics |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

---

## Docker Architecture

Docker Compose runs the complete local integration environment.

```text
Docker Compose
│
├── FastAPI
│     └── Port 8000
│
├── PostgreSQL
│     └── Internal Port 5432
│
├── Prometheus
│     └── Port 9090
│
└── Grafana
      └── Port 3000
```

Prometheus communicates with FastAPI using:

```text
http://api:8000/metrics
```

inside the Docker network.

---

## Database

PostgreSQL is used to persist EDI transaction records.

The main transaction table stores:

```text
filename
status
control_number
purchase_order_number
erp_order_number
error_message
created_at
```

SQLAlchemy is used as the ORM layer.

Alembic is used to manage database schema migrations.

---

## Testing

Run the automated test suite with:

```bash
pytest
```

The test suite covers scenarios including:

- Health endpoint
- Valid X12 upload
- Invalid quantity
- Transaction history
- ERP purchase order creation
- Duplicate control number
- ERP retry behavior
- Missing API key
- Missing ISA segment
- Incomplete ISA segment
- Missing control number
- Missing BEG segment
- Missing purchase order number
- Incomplete BEG segment
- Missing order date
- Invalid order date
- Missing buyer
- Missing supplier
- Missing PO1
- Missing SKU
- Invalid unit price
- Unsupported file extension
- Invalid file encoding
- Missing item unit

---

## Project Structure

```text
ediflow-canada/
│
├── backend/
│   └── app/
│       │
│       ├── core/
│       │   ├── logging_config.py
│       │   ├── metrics.py
│       │   └── security.py
│       │
│       ├── db/
│       │   ├── database.py
│       │   ├── models.py
│       │   └── service.py
│       │
│       ├── edi/
│       │   ├── exceptions.py
│       │   ├── x12_parser.py
│       │   └── x12_validator.py
│       │
│       ├── erp/
│       │   ├── router.py
│       │   ├── schemas.py
│       │   └── service.py
│       │
│       └── main.py
│
├── edi_samples/
│   └── x12/
│
├── tests/
│   └── test_api.py
│
├── docs/
│   └── images/
│       ├── ediflow-architecture.png
│       ├── grafana-dashboard.png
│       ├── prometheus-target.png
│       └── transaction-history.png
│
├── alembic/
├── Dockerfile
├── docker-compose.yml
├── prometheus.yml
├── requirements.txt
├── .env.example
├── .gitignore
├── .dockerignore
└── README.md
```

---

## Business Scenario

EDIFlow Canada represents a typical B2B integration workflow used between trading partners and ERP systems.

A customer or trading partner sends an ANSI X12 850 Purchase Order to the integration platform.

The platform then:

1. Receives the X12 transaction through a REST API.
2. Authenticates the API request.
3. Parses the EDI segments.
4. Validates business-critical information.
5. Checks for duplicate transactions.
6. Maps the transaction into an ERP-compatible structure.
7. Sends the purchase order to the ERP integration layer.
8. Retries temporary ERP failures.
9. Records completed, rejected, or failed outcomes.
10. Stores an audit trail in PostgreSQL.
11. Exposes operational metrics through Prometheus.
12. Visualizes transaction health in Grafana.

This project demonstrates concepts commonly used in:

- EDI integration platforms
- B2B integration
- ERP integration
- SaaS integration systems
- Backend integration services
- Data integration platforms
- Integration monitoring
- Production support environments

---

## Why I Built This Project

My professional background includes working with **EDI, ERP, API, and B2B integrations**, including customer onboarding, document mapping, validation, troubleshooting, and production support.

EDIFlow Canada was built to extend that experience into a modern North American integration stack using:

```text
ANSI X12
Python
FastAPI
PostgreSQL
Docker
Prometheus
Grafana
```

The project combines traditional EDI integration concepts with modern backend engineering, API design, containerization, database persistence, automated testing, and observability.

---

## Future Enhancements

Planned extensions include support for additional ANSI X12 transaction sets.

### X12 855

Purchase Order Acknowledgment

```text
850 -> 855
```

### X12 856

Advance Ship Notice

```text
850 -> 855 -> 856
```

### X12 810

Invoice

```text
850 -> 855 -> 856 -> 810
```

### X12 997 / 999

Functional and Implementation Acknowledgments

### X12 860

Purchase Order Change

Additional potential enhancements include:

- Real ERP API integration
- Message queue integration
- Asynchronous processing
- Cloud deployment
- Centralized logging
- Alerting
- Role-based authentication
- Trading partner configuration
- EDI mapping management
- Additional monitoring metrics

---

## Author

**Grishma Khatra**

Master of Computer Science  
Lakehead University, Canada

Professional focus:

- EDI & B2B Integration
- ERP Integration
- API Integration
- Data Integration
- Backend Engineering
- Integration Support
- Monitoring & Observability

GitHub: [Grishmakhatra932](https://github.com/Grishmakhatra932)