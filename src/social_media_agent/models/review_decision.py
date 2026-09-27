from typing import Literal

from pydantic import BaseModel


class ReviewDecision(BaseModel):
    decision: Literal[
        "approved",
        "rejected",
    ]

    note: str = ""

    publication_plan_id: str | None = None
