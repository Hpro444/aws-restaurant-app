"""DTOs for the GET /locations endpoint."""

from pydantic import BaseModel, ConfigDict


class LocationResponse(BaseModel):
    """One location card returned by GET /locations."""

    model_config = ConfigDict(extra="ignore")

    id: str
    address: str
    description: str
    total_capacity: str
    average_occupancy: str
    image_url: str
    rating: str


class LocationNameResponse(BaseModel):
    """One location option returned by GET /locations/select-options."""

    model_config = ConfigDict(extra="ignore")

    location_id: str
    location_address: str
