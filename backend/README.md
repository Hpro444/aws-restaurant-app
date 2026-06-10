# Restaurant Backend

AWS Lambda + API Gateway backend for the restaurant management platform. Three Lambda functions handle all traffic: `ApiHandler` routes HTTP requests, `DataCaptureLambda` processes async SQS events to maintain report aggregates, and `ReportSenderLambda` emails weekly CSV reports via SES. DynamoDB is the primary store; AWS Cognito handles authentication.

---

## Tech stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.13 |
| Framework | AWS Syndicate (Lambda + API Gateway) |
| Database | DynamoDB |
| Auth | AWS Cognito (USER_PASSWORD_AUTH) |
| Async events | AWS SQS |
| Email reports | AWS SES |
| Validation | Pydantic v2 |
| Logging | structlog |
| Tests | pytest + unittest.mock |

---

## Project layout

```
restaurant-backend-app/
├── pyapp/
│   ├── src/
│   │   ├── lambdas/
│   │   │   ├── api-handler/             # HTTP entry point; route dispatch
│   │   │   ├── data_capture_lambda/     # SQS consumer; updates report aggregates
│   │   │   └── report_sender_lambda/    # Scheduled; emails weekly CSV via SES
│   │   ├── services/                    # Business logic
│   │   ├── repositories/               # DynamoDB access (generic DynamoRepository[T])
│   │   ├── domain/                     # Persistent entity models (DynamoModel)
│   │   ├── dto/                        # Request / response Pydantic models
│   │   ├── enums/                      # HttpStatusCode, UserRole, etc.
│   │   └── commons/                    # AbstractLambda, LambdaResponse, exceptions, AppConfig
│   └── tests/                          # pytest unit tests (no real AWS calls)
└── README.md
```

---

## API endpoints

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/sign-up` | — | Register a new user |
| POST | `/auth/sign-in` | — | Authenticate and receive tokens |
| POST | `/auth/refresh` | — | Refresh access token |
| POST | `/auth/logout` | — | Revoke refresh token |

### Users

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/users/profile` | Any | Fetch the authenticated user's profile |
| PUT | `/users/profile` | Any | Update the authenticated user's profile |
| GET | `/users/waiter/location` | Waiter | Return the waiter's assigned location |

### Locations

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/locations` | — | List all restaurant locations |
| GET | `/locations/{id}` | — | Get a single location |
| GET | `/locations/select-options` | — | Location id + address pairs for pickers |
| GET | `/locations/{id}/valid-slot-times` | — | Valid slot start/end times for a location |
| GET | `/locations/{id}/speciality-dishes` | — | Speciality dishes for a location |
| GET | `/locations/{id}/feedbacks` | — | Paginated feedbacks for a location |
| GET | `/locations/{id}/tables` | Waiter | All tables at a location |

### Bookings

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/bookings/tables` | — | Available tables with free slots (customer view) |
| GET | `/bookings/waiter/tables` | Waiter | Available tables with free slots (waiter view) |
| POST | `/bookings/client` | Customer / Waiter | Create a reservation |
| GET | `/bookings/client` | Customer / Waiter | Dashboard reservations list |
| GET | `/bookings/client/{reservationId}` | Customer / Waiter | Get a single reservation |
| PUT | `/bookings/client/{reservationId}` | Customer / Waiter | Update reservation status |
| PUT | `/bookings/waiter/{reservationId}` | Waiter | Waiter-only reservation status update |
| DELETE | `/bookings/client/{reservationId}/cancel` | Customer / Waiter | Cancel a reservation |

### Reservations

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/reservations/waiter` | Waiter | Table-filtered waiter reservation view |

### Dishes

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/dishes` | — | List dishes (filterable by type, sort, dietary) |
| GET | `/dishes/popular` | — | List all popular dishes |
| GET | `/dishes/{id}` | — | Get a single dish |

### Feedbacks

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/feedbacks/context/{reservationId}` | Customer | Feedback modal data for a reservation |
| POST | `/feedbacks` | Customer | Submit feedback |
| PUT | `/feedbacks` | Customer | Update feedback |

### Orders

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/orders` | Waiter | Create an order for a reservation |

### Customers & Reports

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/customers` | Waiter | List all customers |
| GET | `/reports` | Admin | Aggregated reports filtered by type, period, location |

---

## Async SQS pipeline

`ApiHandler` publishes events to SQS whenever a reservation changes status or feedback is submitted. `DataCaptureLambda` consumes these events and incrementally updates two report-aggregate tables:

- **WaiterReport** — per-waiter metrics (reservations, orders, revenue, ratings) keyed by ISO week.
- **LocationReport** — per-location metrics (reservations, revenue, cuisine/service feedback averages) keyed by ISO week.

`ReportSenderLambda` runs on a schedule, reads the current ISO-week aggregates, generates CSV attachments, and sends the weekly summary via SES to configured admin recipients.

---

## Request lifecycle

1. AWS invokes `lambda_handler(event, context)` → delegates to the `HANDLER` singleton.
2. `handle_request()` matches path + method and dispatches to the correct route method.
3. Each route method calls `_parse_body()` / `_parse_query_params()` then `_validate(PydanticModel, payload)`.
4. The service layer executes business logic; the repository layer performs DynamoDB I/O.
5. `build_response(data, code)` wraps a successful result. Errors raise `ApplicationException`, caught by `AbstractLambda`.

---

## Error responses

All validation failures (HTTP 422) return a consistent JSON body:

```json
{
  "errors": [
    { "field": "email", "message": "email local part must start with a letter" }
  ]
}
```

Modelled by `ValidationErrorResponse` / `FieldError` in `dto/error_response.py`.

---

## Auth rules

- **Email normalization** — emails are lowercased and stripped on both sign-up and sign-in.
- **Email format** — on sign-up, the local part (before `@`) must start with a letter.
- **Password policy** — 8–16 characters, requires uppercase, lowercase, digit, and special character.
- **Login lockout** — account is locked for 15 minutes after 5 consecutive failed attempts (configurable via `MAX_LOGIN_ATTEMPTS` / `LOCKOUT_SECONDS`).
- **Role assignment** — `RegistrationService` checks the `waiter-emails` table to assign Waiter vs. Customer; admins are assigned via the `admin-emails` table.

---

## Running tests

From `backend/` (where `pyproject.toml` lives):

```bash
# All tests
python -m pytest

# Single file
python -m pytest restaurant-backend-app/pyapp/tests/test_api_handler/test_sign_in.py

# Single test
python -m pytest restaurant-backend-app/pyapp/tests/test_api_handler/test_sign_in.py::TestSignIn::test_success_returns_200_with_tokens_username_role

# With coverage
python -m pytest --cov=restaurant-backend-app/pyapp/src
```

Tests use `unittest.mock` — no real AWS calls are made.

---

## Dependencies

**Runtime** (`pyapp/src/lambdas/api-handler/requirements.txt`):

| Package | Version |
|---|---|
| aws-lambda-powertools | 3.29.0 |
| pydantic[email] | 2.13.4 |
| pydantic-settings | 2.0.0 |
| structlog | 25.5.0 |
| pyjwt | 2.12.1 |

**Development** (`pyproject.toml`):

| Package | Version |
|---|---|
| pytest | 9.0.3 |
| pytest-cov | >=7.1.0 |
| boto3 | 1.38.12 |
| ruff | 0.15.15 |
| pre-commit | 4.6.0 |
| requests | >=2.32.0 |
| fpdf2 | >=2.8.0 |
| argon2-cffi | 23.1.0 |
