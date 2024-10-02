"""
Module gathering the schemas of bodies and responses of the end points.
"""

from typing import Any

from pydantic import BaseModel


class CodeRequest(BaseModel):
    cellId: str
    code: str
    capturedIn: dict[str, Any]
    capturedOut: list[str]
