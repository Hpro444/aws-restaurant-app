# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [1.0.1] - 2026-05-20

### Fixed

- PATCH Improved account lockout message and refactored user registration method in `cognito_service`.
- PATCH Added missing tests for reservation management and sign-in flow.
- PATCH Changed booking cancellation HTTP method from PUT to DELETE to follow REST semantics.

## [1.0.0] - 2026-05-20

Full-featured restaurant API with all core endpoints, reservation management, feedback, and dishes.

### Added

- MINOR Implemented GET `/dishes` endpoints for most popular dishes across all locations and location-specific specialties (`feature/api-get-dishes`).
- MINOR Implemented GET `/locations` endpoint for retrieving general information about all restaurant locations (`feature/api-locations`).
- MINOR Implemented GET `/feedbacks` endpoint for retrieving location feedbacks filtered by criteria (`feature/api-feedbacks`).
- MINOR Implemented reservation management endpoints (list and cancel reservations) in `ApiHandler` with full test coverage (`feature/reservation-business-rules`).
- MINOR Added rating field to `Feedback` model; `LocationsService` now computes and returns average rating per location.
- MINOR Added `average_occupancy` simulation for restaurant locations.
- MINOR Implemented deterministic waiter assignment to reservations based on location.
- MINOR Added global secondary indexes (GSI) for reservations and slots to enable queries by customer and waiter IDs.
- MINOR Added multi-slot booking business rules with turnover-gap tolerance between consecutive 90-minute slots.

### Changed

- PATCH Refactored `WaiterRepository` to use GSI query for location-based waiter retrieval.
- PATCH `total_capacity` is now computed automatically from table data.
- PATCH Refactored `LocationsService` and related test cases for improved readability and consistency.

### Fixed

- PATCH Corrected sign-in response message format (`fix/sign-in-correct-response`).

## [0.6.0] - 2026-05-19

CORS support, frontend auth context, signup page, and locations API groundwork.

### Added

- MINOR Added CORS support to all Lambda responses and configured allowed origin in app settings (`fix/cors`).
- MINOR Implemented GET `/locations` endpoint with CORS support and initial location service.
- MINOR Added admin `PUT /users/profile` route and admin role infrastructure (`feature/admin`).
- MINOR Implemented booking `POST` endpoint for customer reservations (`feature/booking_post`).
- MINOR Added frontend signup page with structure and form (`feature/ui-signup`).
- MINOR Implemented frontend session management; content rendered based on user role (`feature/ui-auth-context`).
- MINOR Added frontend component for displaying backend status responses (login/register flows).
- MINOR Added frontend email validation so email cannot start with an invalid character.
- MINOR Added DTOs for reservation management and updated request validation logic.

### Changed

- PATCH Updated `deployment_resources.json` to remove trailing slashes from `custom_origins`.
- PATCH Enabled CORS for authentication and user profile endpoints.

### Fixed

- PATCH Reverted a broken merge of `fix/tests` from `main`.
- PATCH Fixed Python version problem in Lambda handler.

## [0.5.0] - 2026-05-18

User profile endpoints, admin role, seeding, and dependency fixes.

### Added

- MINOR Implemented `GET /users/profile` endpoint for user profile information retrieval (`feature/api-get-user-profile`).
- MINOR Added `PUT /users/profile` endpoint for updating user profile data.
- MINOR Added admin role support with associated repositories and waiter-email allow-list (`feature/admin`).
- MINOR Implemented seeding modules for locations, customers, dishes, tables, slots, reservations, and feedback (`feature/seeds`).
- MINOR Added quick seed script for populating AWS DynamoDB with demo data (with pagination).
- MINOR Added unit tests for user profile retrieval.

### Changed

- PATCH Refactored JWT decoding logic and moved it to a separate utility module (`fix/jwt`).
- PATCH Refactored user profile service and Cognito service for improved clarity and structure (`feature/refactor-get-user-profile`).
- PATCH Refactored user role checks to use enum directly instead of string comparisons.

### Fixed

- PATCH Pinned `structlog` version and added `pyjwt` dependency in requirements (`fix/requirements`).

## [0.4.0] - 2026-05-17

Table availability endpoint, automatic role assignment, and DynamoDB index standardisation.

### Added

- MINOR Implemented `GET /bookings/tables` — `TableAvailabilityService` computes available tables and slots for a given location and date with optional time window filters (`feature/table-availability`).
- MINOR Implemented automatic role assignment during user registration based on waiter-emails whitelist (`feature/automatic-role-assignment`).
- MINOR Added domain model and DynamoDB repository for waiter-email records.
- MINOR Added `Visitor` role; renamed `User` role to `Customer` in the roles enum.
- MINOR Added DTOs for table availability request and response handling.
- MINOR Added comprehensive tests for `TableAvailabilityService`, registration service, and automatic role assignment.

### Changed

- PATCH Standardised DynamoDB index naming conventions across deployment resource definitions.
- PATCH Refactored `get_available_tables` to accept `location_id` as UUID or string.
- PATCH Refactored table availability request DTO to validate `location_id` as UUID and tighten `guests_number` constraints.
- PATCH Refactored `location_id` field in table and user models for consistency.

## [0.3.0] - 2026-05-14

Database layer with DynamoDB models, repositories, and full frontend scaffolding.

### Added

- MINOR Configured all DynamoDB tables (waiters, customers, locations, tables, dishes, shifts, slots, reservations, feedback) and updated Lambda environment variables (`feature/database-models`).
- MINOR Added domain models for dish, feedback, location, reservation, shift, slot, table, and user.
- MINOR Refactored domain models to use Pydantic `BaseModel` and introduced DynamoDB repositories for CRUD operations.
- MINOR Refactored login-attempts service to use repository pattern.
- MINOR Added tests for repository and model operations.
- MINOR Frontend: added header, router, login page structure, signup form with form validations.
- MINOR Extracted CSS color variables for reuse across the frontend project.

### Changed

- PATCH Updated Lambda runtime to Python 3.13.
- PATCH Refactored DynamoDB model serialization.
- PATCH Updated dependencies and added pip.

## [0.2.0] - 2026-05-13

Authentication endpoints complete — sign-in, logout, refresh token, and account lockout.

### Added

- MINOR Implemented sign-in endpoint with Cognito `initiate_auth` and structured response (access token, username, role) (`feature/sign-in_log_out_refresh`).
- MINOR Implemented logout endpoint that revokes refresh tokens.
- MINOR Implemented refresh token endpoint.
- MINOR Implemented account lockout mechanism after repeated failed login attempts (`feature/sign-in_lockout`).
- MINOR Added JWT service for token generation; sign-in now returns a signed JWT.
- MINOR Added `pydantic-settings` dependency for configuration management.
- MINOR Migrated frontend to TypeScript and installed Tailwind CSS (`feature/migration-to-typescript`).
- MINOR Set up backend tooling and project configuration (`feature/project-setup-local`).

### Changed

- PATCH Refactored Cognito service to use `AppConfig` for settings.
- PATCH Updated sign-up and sign-in request models to use `SecretStr` for password handling.
- PATCH Standardised string formatting and improved code readability.
- PATCH Updated dependency versions to fixed values.
- PATCH Removed email normalisation from sign-up and sign-in request models.
- PATCH Improved logging configuration and enhanced context handling in `log_helper`.
- PATCH Enhanced response handling and logging in Lambda functions.

## [0.1.0] - 2026-05-11

Initial project setup with AWS Lambda API handler, Cognito-backed user registration, and sign-in stub.

### Added

- MINOR Created API handler Lambda function (`feature/add-lambda-api-handler`).
- MINOR Added API Gateway and Cognito User Pool resources to deployment configuration.
- MINOR Added sign-up endpoint to API Gateway.
- MINOR Implemented user registration with Cognito integration including validation and error handling.
- MINOR Added sign-in endpoint with authentication logic and request/response models (`feature/register_endpoint`).
- MINOR Introduced HTTP status code enum for improved response clarity.
- MINOR Added initial project files: `.gitignore`, README, deployment resources.
- MINOR Generated React frontend boilerplate.
- MINOR Added Python version and `pyproject.toml` project configuration.
