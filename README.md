# Restaurant Management Platform

A serverless restaurant management platform built on AWS. The system handles table reservations, menus, customer profiles, waiter workflows, customer feedback, orders, and automated weekly reports.

---

## Repository layout

```
restaurant-app/
├── backend/          # Python serverless backend (AWS Lambda + API Gateway + DynamoDB)
├── frontend/         # Web client
└── automation-qa/    # End-to-end API test suite
```

---

## Components

### Backend

Python 3.13 serverless backend deployed via AWS Syndicate. Three Lambda functions cover all API traffic, async SQS data capture, and scheduled weekly report emails. DynamoDB is the primary store; Cognito manages authentication.

See [backend/README.md](backend/README.md) for architecture, endpoints, and test instructions.

### Frontend

Web client for the restaurant platform.

See [frontend/README.md](frontend/README.md).

### Automation QA

End-to-end tests that deploy an isolated AWS environment, seed fixture data, hit every API route in dependency order, and produce a `test_output.pdf` report.

See [automation-qa/README.md](automation-qa/README.md) for setup and run instructions.

---

## Tech stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.13 |
| Deployment | AWS Syndicate |
| Compute | AWS Lambda |
| API | AWS API Gateway |
| Database | DynamoDB |
| Auth | AWS Cognito |
| Async events | AWS SQS |
| Email reports | AWS SES |
| Validation | Pydantic v2 |
| Logging | structlog |
| Tooling | uv, ruff, pytest |

---

## Quick start

```bash
# Install dependencies (from backend/)
uv sync

# Run unit tests
python -m pytest

# Run the full e2e pipeline (from automation-qa/)
.\run_e2e.ps1     # Windows
./run_e2e.sh      # Linux / macOS
```
