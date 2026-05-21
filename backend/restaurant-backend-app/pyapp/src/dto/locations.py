"""DTOs for the GET /locations endpoint."""

from pydantic import BaseModel, ConfigDict


class LocationResponse(BaseModel):
    """One location card returned by GET /locations."""

    model_config = ConfigDict(extra="ignore")

    id: str
    address: str
    description: str
    total_capacity: int
    average_occupancy: int
    image_url: str
    rating: float


class LocationAddressResponse(BaseModel):
    """One location option returned by GET /locations/select-options."""

    model_config = ConfigDict(extra="ignore")

    # TODO: skrati da bude "id" i "address", azuriraj swagger, obavesti frontend
    location_id: str
    location_address: str
