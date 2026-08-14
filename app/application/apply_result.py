from pydantic import BaseModel


class ApplyResult(BaseModel):

    submitted: bool

    mode: str

    message: str
