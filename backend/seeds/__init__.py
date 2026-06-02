"""Seeds package for restaurant app DynamoDB demo data.

Each module exposes a single ``seed(dynamodb, tables, context)`` function.
``SEED_ORDER`` defines the execution order — some seeders depend on data
written to ``context`` by earlier ones.
"""

SEED_ORDER = [
    "cognito_users",
    "locations",
    "customers",
    "waiters",
    "admin_emails",
    "waiter_emails",
    "tables",
    "dishes",
    "slots",
    "shifts",
    "reservations",
    "reservation_waiter_view",
    "feedback_cuisine",
    "feedback_service",
]
