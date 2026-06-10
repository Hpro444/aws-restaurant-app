"""Static configuration shared by all e2e suites."""

AWS_REGION = "eu-west-3"
STAGE = "api"

# Password used by quick_seed.py for every seeded Cognito user, reused for
# the user registered during the auth suite.
SEED_PASSWORD = "Password123@"

# Logical table aliases (syndicate_aliases.yml keys without the ``_table``
# suffix) that the suites snapshot for before/after database verification.
TRACKED_TABLE_ALIASES = [
    "customers",
    "waiters",
    "locations",
    "tables",
    "dishes",
    "slots",
    "reservations",
    "orders",
    "feedback_cuisine",
    "feedback_service",
]

# Fixed actors, mirroring test_sqs_endpoints.py: max is the Airport table-1
# first-shift waiter and kate is the showcase customer.  Note: the seeder
# books the two earliest slots of every waiter for each of the next six days
# (current-week report data), so suites must never assume the first listed
# availability windows are bookable — see bookings._capture_slots.
CUSTOMER_EMAIL = "kate@example.com"
WAITER_EMAIL = "max@example.com"
