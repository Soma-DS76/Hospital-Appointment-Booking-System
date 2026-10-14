from pydantic import BaseModel, ConfigDict


class HealthStatus(BaseModel):
    status: str
    database: str
    uploads_dir: str
    environment: str

    model_config = ConfigDict(from_attributes=True)
