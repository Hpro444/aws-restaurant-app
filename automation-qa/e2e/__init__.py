"""End-to-end test suites for every API route of the restaurant backend.

Each module exposes a single ``run(ctx)`` function that executes the HTTP
calls for one route group, asserts the responses, and verifies the related
DynamoDB state.  ``SUITE_ORDER`` defines the execution order — later suites
depend on entities (reservations, orders, feedback) created by earlier ones,
mirroring how ``seeds.SEED_ORDER`` chains its seed modules.
"""

SUITE_ORDER = [
    "auth",
    "locations",
    "dishes",
    "users",
    "customers",
    "reports",
    "bookings",
    "orders",
    "waiter_reservations",
    "bookings_lifecycle",
    "feedbacks",
    "sqs",
]
