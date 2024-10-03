"""
Module gathering the schemas of bodies and responses of the end points.
"""

from typing import Any

from pydantic import BaseModel


class RunBody(BaseModel):
    """
    Body for the endpoint `/run`.
    """

    cellId: str
    """
    Cell's ID
    """
    code: str
    """
    Code to run.
    """
    capturedIn: dict[str, Any]
    """
    Captured input variables.
    """
    capturedOut: list[str]
    """
    Name of the captured output variables.
    """


class RunResponse(BaseModel):
    """
    Response for the endpoint `/run`.
    """

    output: str
    """
    Std output.
    """
    error: str
    """
    Std error.
    """
    capturedOut: dict[str, Any]
    """
    Value of the capture output.
    """
