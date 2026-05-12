from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    """
    Typed return value for every domain agent (HR, IT, Finance).

    Why Pydantic here instead of plain dict:
    - Validation catches missing/wrong-type fields at agent boundary,
      not silently in the UI.
    - IDE autocomplete works everywhere this is used.
    - Adding a new field is a one-line change with immediate compile-time
      visibility across all consumers.
    - model_dump() produces the wire format the workflow graph expects.
    """
    answer: str = Field(..., description="Human-readable response text")
    confidence: int = Field(default=50, ge=0, le=100)
    source: str = Field(default="internal_kb")
    keyword_match: bool = Field(default=False)
    rag_used: bool = Field(default=False)
    # Optional — set by agents that trigger real action execution
    action_triggered: bool = Field(default=False)
    action_type: str | None = Field(default=None)
    action_payload: dict | None = Field(default=None)
