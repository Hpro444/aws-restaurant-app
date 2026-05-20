# Restaurant Backend

AWS Lambda + API Gateway backend for the restaurant management platform. A single Lambda function (`ApiHandler`) routes all requests by inspecting `event["path"]` and `event["httpMethod"]`. DynamoDB is the primary store; AWS Cognito handles authentication.

---

## Tech stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.14 |
| Framework | AWS Syndicate (Lambda + API Gateway) |
| Database | DynamoDB |
| Auth | AWS Cognito (USER_PASSWORD_AUTH) |
| Validation | Pydantic v2 |
| Logging | structlog |
| Tests | pytest + unittest.mock |

---

## Project layout

```
restaurant-backend-app/
├── pyapp/
│   ├── src/
│   │   ├── lambdas/api-handler/
│   │   │   ├── handler.py          # Entry point; route dispatch
│   │   │   └── requirements.txt    # Lambda runtime dependencies
│   │   ├── services/               # Business logic
│   │   ├── repositories/           # DynamoDB access (generic DynamoRepository[T])
│   │   ├── domain/                 # Persistent entity models (DynamoModel)
│   │   ├── dto/                    # Request / response Pydantic models
│   │   ├── enums/                  # HttpStatusCode, UserRole, etc.
│   │   └── commons/                # AbstractLambda, LambdaResponse, exceptions, AppConfig
│   └── tests/                      # pytest tests (no real AWS calls)
├── CHANGELOG.md
└── README.md
```

---

## API endpoints

### Auth

| Method | Path | Description |
|---|---|---|
| POST | `/auth/sign-up` | Register a new user |
| POST | `/auth/sign-in` | Authenticate and receive tokens |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Revoke refresh token |

### Users

| Method | Path | Description |
|---|---|---|
| GET | `/users/profile` | Fetch the authenticated user's profile |
| PUT | `/users/profile` | Update the authenticated user's profile |

### Locations

| Method | Path | Description |
|---|---|---|
| GET | `/locations` | List all restaurant locations |
| GET | `/locations/{id}` | Get a single location |
| GET | `/locations/{id}/speciality-dishes` | Get speciality dishes for a location |
| GET | `/locations/{id}/feedbacks` | Get paginated feedbacks for a location |

### Bookings

| Method | Path | Description |
|---|---|---|
| GET | `/bookings/tables` | List available tables (with free time slots) |
| POST | `/bookings/client` | Create a reservation |
| GET | `/bookings/client` | List the authenticated user's reservations |
| GET | `/bookings/client/{id}` | Get a single reservation |
| PUT | `/bookings/client/{id}` | Update reservation status |
| DELETE | `/bookings/client/{id}/cancel` | Cancel a reservation |

### Dishes

| Method | Path | Description |
|---|---|---|
| GET | `/dishes/popular` | List popular dishes |

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

- **Email normalization** — emails are lowercased and stripped on both sign-up and sign-in, so `User@Example.COM` and `user@example.com` resolve to the same account.
- **Email format** — on sign-up, the local part (before `@`) must start with a letter.
- **Password policy** — 8–16 characters, requires uppercase, lowercase, digit, and special character.
- **Login lockout** — account is locked for 15 minutes after 5 consecutive failed attempts (configurable via `MAX_LOGIN_ATTEMPTS` / `LOCKOUT_SECONDS`).
- **Role assignment** — `RegistrationService` checks the `waiter-emails` table to assign Waiter vs. Customer; admins are assigned via the `admin-emails` table.

---

## Running tests

From the repo root (`restaurant-backend-app/`):

```bash
# All tests
python -m pytest pyapp/tests/

# Single file
python -m pytest pyapp/tests/test_api_handler/test_sign_in.py

# Single test
python -m pytest pyapp/tests/test_api_handler/test_sign_in.py::TestSignIn::test_success_returns_200_with_tokens_username_role

# With coverage
python -m pytest pyapp/tests/ --cov=pyapp/src
```

Tests use `unittest.mock` — no real AWS calls are made.

---

## Dependencies

**Runtime** (`pyapp/src/lambdas/api-handler/requirements.txt`):

| Package | Version |
|---|---|
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
| ruff | latest |
| pre-commit | 4.6.0 |

---

## Changelog

<!-- CHANGELOG -->
### [1.1.0] - 2026-05-20
- Added `ValidationErrorResponse` / `FieldError` DTOs; all 422 responses now return `{"errors": [...]}`
- Email normalization (lowercase + strip) on sign-up and sign-in
- Email local-part must start with a letter on sign-up
- Comprehensive README documentation

### [1.0.1] - 2026-05-20
- Fixed account lockout message; added missing reservation and sign-in tests
- Changed booking cancellation from PUT to DELETE

### [1.0.0] - 2026-05-20
- Full-featured restaurant API: locations, feedbacks, dishes, reservations, multi-slot bookings, waiter assignment, GSI queries

> Full history: [CHANGELOG.md](CHANGELOG.md)
<!-- /CHANGELOG -->
