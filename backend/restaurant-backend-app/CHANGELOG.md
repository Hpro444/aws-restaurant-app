# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.0] - 2026-05-28

### Added
- `dto/feedbacks.py` — three new Pydantic DTOs for the feedbacks endpoint: `FeedbackResponse` (single item), `FeedbackPageableResponse` (pagination metadata), and `PageFeedbackResponse` (full paginated wrapper); all fields use camelCase aliases for JSON serialization via `model_dump(by_alias=True)`
- `FeedbackService._build_feedback_response()` — private helper that maps a `Feedback` domain object to `FeedbackResponse`; when `customer_id` is set it looks up the customer record and overwrites `user_name` / `user_image_url` with the customer's actual profile data
- `CustomerRepository` injected into `FeedbackService` for customer profile enrichment during response construction
- Structured logging added to `FeedbackService.get_feedbacks()` — logs retrieval parameters, repository result count, and final page metadata

### Changed
- `Feedback` base domain model: `user_image` field renamed to `user_image_url`; new `user_name` field added alongside it
- `FeedbackService.get_feedbacks()` return type changed from `dict[str, Any]` to the typed `PageFeedbackResponse`; internally builds the response via `_build_feedback_response()` instead of assembling a raw dict
- `handler.py` feedbacks route: validates the service response through `PageFeedbackResponse.model_validate()` and serializes with `model_dump(by_alias=True, mode="json")` so all paginated fields are emitted in camelCase
- Pagination out-of-range error message updated to `"Requested page {page} exceeds available pages."` (was `"Must be between 0 and {max_page}"`)
- Swagger UI schema updated to reflect the new `FeedbackResponse` shape (`user_name`, `user_image_url`) and camelCase paginated response fields
- Seed data updated in `feedback_cuisine.py` and `feedback_service.py` to use the renamed `user_image_url` and new `user_name` fields

## [1.4.0] - 2026-05-28

### Added
- `seeds/config.py` — single source of truth for all seed constants (`AWS_REGION`, `SLOT_SEED_DAYS_AHEAD`, `SLOT_DURATION_MINUTES`, `SLOT_BREAK_MINUTES`, `THREAD_WORKERS`, `DYNAMO_RETRY_CONFIG`, `SEED_NAMESPACE`); all seed modules and `quick_seed.py` import from here instead of defining their own copies
- `http://localhost:5173` added to the CORS allowed-origins list in `AppConfig`; `AbstractLambda` now reflects the request `Origin` header back when it matches the allowlist, falling back to the primary S3 origin otherwise

### Changed
- Slot seeding parallelised with `ThreadPoolExecutor(max_workers=7)` — one worker per calendar day; each worker opens its own `boto3.session.Session` and dedicated DynamoDB connection, writes all slots for that day via `batch_writer`, then explicitly closes the connection
- On any `ClientError` during a day's write the worker closes the bad connection and opens a fresh one before retrying, so throttling errors or transient failures always get a clean connection
- DynamoDB resource created with `botocore.config.Config(retries={"mode": "adaptive", "max_attempts": 20})` so each worker self-limits its request rate under `ProvisionedThroughputExceededException` instead of failing after the default retry budget
- `SEED_NAMESPACE` UUID moved from `seeds/utils.py` into `seeds/config.py`; `seeds/utils.py` now imports it from there

## [1.3.0] - 2026-05-21

### Added
- Swagger UI API documentation endpoint for interactive exploration of all backend routes (`feature/api-swagger-docs`)
- `user_image` field on the `Feedback` base domain model — stored in DynamoDB and included in the feedbacks API response so reviewers' avatars are available without a separate customer lookup

### Changed
- **Seed dishes**: each of the three restaurant locations now has exactly 4 specialty dishes; every dish carries a unique image drawn from the 4 available S3 food assets (`dish1_img.png`, `ChocolateMoussewithBerries.png`, `PineappleTartwithVanillaSouffle.png`, `avocado_pine_nut_bowl.png`)
- **Seed customers**: avatar URLs now cycle through the 4 real S3 images (`user_avatar_1.png`, `user_avatar_2.png`, `user_avatar_3.png`, `user_avatar_default.png`), replacing the previously referenced non-existent files (`user_avatar_4.png` … `user_avatar_11.png`)
- **Seed feedback**: completely rebuilt — each of the 11 customers now has exactly 2 cuisine-feedback entries per restaurant location and 2 service-feedback entries per waiter (66 entries per feedback type, up from 30); every entry embeds the reviewer's `user_image` URL directly in the record
- Refactored dish specialties and slot seeding so that tomorrow's slots are always available for demo use
- Enhanced CORS headers on all Lambda responses; customer and dish seeding logic updated for improved demo data quality (`bcd40a8`)
- `LocationAddressResponse` DTO corrected to return the proper field types (`fix/correct-dto-response-types`)
- Pydantic model configurations updated across domain and DTO models: whitespace stripping on string fields, minimum length enforcement, and `extra="ignore"` for forward compatibility (`89cf78c`, `75fefd4`)
- Error response format unified to consistent JSON structure `{"errors": [{"field": "...", "message": "..."}]}` across all API handlers (`fix/api-json-message-format`)

### Fixed
- Sign-up flow: two separate rounds of regression fixes (`fix/sign_up` × 2)
- Registration service tests updated to reflect the correct return value on successful sign-up (`fix/cognito_tests`)
- Most popular dishes endpoint corrected to handle all locations consistently (`fixt/tests`)
- Post-first-demo bug fixes across various API features and UI edge cases (`builds/last_build`)

## [1.2.0] - 2026-05-21

### Added
- Expanded test coverage for `TableAvailabilityService` and the available-tables API endpoint with additional edge-case scenarios

### Changed
- Refactored `TableAvailabilityService` to snap `from_time` to the nearest 90-minute slot boundary, ensuring time-window filters align with actual slot intervals
- Updated `AvailableTables` DTO to support the refined slot-aligned filtering parameters
- Updated `handler.py` to pass slot-aligned time parameters through to the availability service
- Replaced placeholder image URLs in all seed modules with real S3-hosted assets: `user_img.png` for customers and waiters, `dish1_img.png` for dishes, `location_img.jpg` for locations

### Fixed
- Minor correction in `FeedbackServiceRepository` import/export

## [1.1.0] - 2026-05-20

### Added
- `ValidationErrorResponse` and `FieldError` Pydantic DTOs in `dto/error_response.py` for structured 422 error bodies
- Email format validation on sign-up: the local part of the email must start with a letter (rejects `_`, digits, dots, etc. as the first character)
- Email normalization (lowercase + strip) on both sign-up and sign-in so `User@Example.COM` and `user@example.com` are treated as the same account
- Comprehensive `README.md` covering architecture, all API endpoints, request lifecycle, auth rules, error format, running tests, and dependency tables

### Changed
- All 422 error responses now use `{"errors": [{"field": "...", "message": "..."}]}` format instead of a bare array, applied consistently across `_validate()`, `_parse_body()`, and all manual validation sites in the handler

## [1.0.1] - 2026-05-20

### Fixed
- Improved account lockout message and refactored user registration method in `cognito_service`
- Added missing tests for reservation management and sign-in flow
- Changed booking cancellation HTTP method from PUT to DELETE to follow REST semantics

## [1.0.0] - 2026-05-20

Full-featured restaurant API with all core endpoints, reservation management, feedback, and dishes.

### Added
- Implemented GET `/dishes` endpoints for most popular dishes across all locations and location-specific specialties
- Implemented GET `/locations` endpoint for retrieving general information about all restaurant locations
- Implemented GET `/feedbacks` endpoint for retrieving location feedbacks filtered by criteria
- Implemented reservation management endpoints (list and cancel reservations) with full test coverage
- Added rating field to `Feedback` model; `LocationsService` now computes and returns average rating per location
- Added `average_occupancy` simulation for restaurant locations
- Implemented deterministic waiter assignment to reservations based on location
- Added global secondary indexes (GSI) for reservations and slots to enable queries by customer and waiter IDs
- Added multi-slot booking business rules with turnover-gap tolerance between consecutive 90-minute slots

### Changed
- Refactored `WaiterRepository` to use GSI query for location-based waiter retrieval
- `total_capacity` is now computed automatically from table data
- Refactored `LocationsService` and related test cases for improved readability and consistency

### Fixed
- Corrected sign-in response message format

## [0.6.0] - 2026-05-19

CORS support, frontend auth context, signup page, and locations API groundwork.

### Added
- Added CORS support to all Lambda responses and configured allowed origin in app settings
- Implemented GET `/locations` endpoint with CORS support and initial location service
- Added admin `PUT /users/profile` route and admin role infrastructure
- Implemented booking `POST` endpoint for customer reservations
- Added DTOs for reservation management and updated request validation logic

### Changed
- Updated `deployment_resources.json` to remove trailing slashes from `custom_origins`
- Enabled CORS for authentication and user profile endpoints

### Fixed
- Reverted a broken merge of `fix/tests` from `main`
- Fixed Python version problem in Lambda handler

## [0.5.0] - 2026-05-18

User profile endpoints, admin role, seeding, and dependency fixes.

### Added
- Implemented `GET /users/profile` endpoint for user profile information retrieval
- Added `PUT /users/profile` endpoint for updating user profile data
- Added admin role support with associated repositories and waiter-email allow-list
- Implemented seeding modules for locations, customers, dishes, tables, slots, reservations, and feedback
- Added quick seed script for populating AWS DynamoDB with demo data (with pagination)
- Added unit tests for user profile retrieval

### Changed
- Refactored JWT decoding logic and moved it to a separate utility module
- Refactored user profile service and Cognito service for improved clarity and structure
- Refactored user role checks to use enum directly instead of string comparisons

### Fixed
- Pinned `structlog` version and added `pyjwt` dependency in requirements

## [0.4.0] - 2026-05-17

Table availability endpoint, automatic role assignment, and DynamoDB index standardisation.

### Added
- Implemented `GET /bookings/tables` — `TableAvailabilityService` computes available tables and slots for a given location and date with optional time window filters
- Implemented automatic role assignment during user registration based on waiter-emails whitelist
- Added domain model and DynamoDB repository for waiter-email records
- Added `Visitor` role; renamed `User` role to `Customer` in the roles enum
- Added DTOs for table availability request and response handling
- Added comprehensive tests for `TableAvailabilityService`, registration service, and automatic role assignment

### Changed
- Standardised DynamoDB index naming conventions across deployment resource definitions
- Refactored `get_available_tables` to accept `location_id` as UUID or string
- Refactored table availability request DTO to validate `location_id` as UUID and tighten `guests_number` constraints
- Refactored `location_id` field in table and user models for consistency

## [0.3.0] - 2026-05-14

Database layer with DynamoDB models, repositories, and full frontend scaffolding.

### Added
- Configured all DynamoDB tables (waiters, customers, locations, tables, dishes, shifts, slots, reservations, feedback) and updated Lambda environment variables
- Added domain models for dish, feedback, location, reservation, shift, slot, table, and user
- Refactored domain models to use Pydantic `BaseModel` and introduced DynamoDB repositories for CRUD operations
- Refactored login-attempts service to use repository pattern
- Added tests for repository and model operations

### Changed
- Updated Lambda runtime to Python 3.13
- Refactored DynamoDB model serialization
- Updated dependencies and added pip

## [0.2.0] - 2026-05-13

Authentication endpoints complete — sign-in, logout, refresh token, and account lockout.

### Added
- Implemented sign-in endpoint with Cognito `initiate_auth` and structured response (access token, username, role)
- Implemented logout endpoint that revokes refresh tokens
- Implemented refresh token endpoint
- Implemented account lockout mechanism after repeated failed login attempts
- Added JWT service for token generation; sign-in now returns a signed JWT
- Added `pydantic-settings` dependency for configuration management

### Changed
- Refactored Cognito service to use `AppConfig` for settings
- Updated sign-up and sign-in request models to use `SecretStr` for password handling
- Standardised string formatting and improved code readability
- Updated dependency versions to fixed values
- Improved logging configuration and enhanced context handling in `log_helper`

## [0.1.0] - 2026-05-11

Initial project setup with AWS Lambda API handler, Cognito-backed user registration, and sign-in stub.

### Added
- Created API handler Lambda function
- Added API Gateway and Cognito User Pool resources to deployment configuration
- Added sign-up endpoint to API Gateway
- Implemented user registration with Cognito integration including validation and error handling
- Added sign-in endpoint with authentication logic and request/response models
- Introduced HTTP status code enum for improved response clarity
- Added initial project files: `.gitignore`, README, deployment resources
- Added Python version and `pyproject.toml` project configuration
