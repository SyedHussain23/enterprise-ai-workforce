from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class QueryRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
    question: str = Field(..., min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class FeedbackRequest(BaseModel):
    workflow_log_id: str = Field(..., description="UUID of the WorkflowLog to rate")
    rating: int = Field(..., ge=1, le=5, description="1=poor, 5=excellent")
    comment: str | None = Field(default=None, max_length=500)


class ActionApprovalRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=500)


class WorkflowResponse(BaseModel):
    status: str
    answer: str
    agent: str
    confidence: int = Field(ge=0, le=100)
    source: str
    steps: list[str]
    confidence_reason: str | None = None
    evaluation_score: float | None = None
    response_time: float
    timestamp: str
    action_id: str | None = None
    action_type: str | None = None
    action_status: str | None = None
