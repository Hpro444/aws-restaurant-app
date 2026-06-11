"""Central configuration for all seed modules."""

from uuid import UUID

from botocore.config import Config

# AWS
AWS_REGION = "eu-west-3"

# Slot generation
SLOT_SEED_DAYS_PAST = 5
SLOT_SEED_DAYS_AHEAD = 7
SLOT_DURATION_MINUTES = 90
SLOT_BREAK_MINUTES = 15

# Thread pool
THREAD_WORKERS = 7

# DynamoDB retry config — adaptive mode applies client-side rate limiting so concurrent
# batch writes back off before hitting ProvisionedThroughputExceededException
DYNAMO_RETRY_CONFIG = Config(retries={"mode": "adaptive", "max_attempts": 10})

# UUID namespace for deterministic seed IDs
SEED_NAMESPACE = UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
