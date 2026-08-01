from pydantic import BaseModel


class InsightOut(BaseModel):
    type: str
    severity: str
    message: str
