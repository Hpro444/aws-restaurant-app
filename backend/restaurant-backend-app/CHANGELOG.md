# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-20
### Added
- `ValidationErrorResponse` and `FieldError` Pydantic DTOs in `dto/error_response.py` for structured 422 error bodies
- Email format validation on sign-up: the local part of the email must start with a letter (rejects `_`, digits, dots, etc. as the first character)
- Email normalization (lowercase + strip) on both sign-up and sign-in so `User@Example.COM` and `user@example.com` are treated as the same account

### Changed
- All 422 error responses now use `{"errors": [{"field": "...", "message": "..."}]}` format instead of a bare array, applied consistently across `_validate()`, `_parse_body()`, and all manual validation sites in the handler
