# standard library
import io
import sys
from typing import Any

# third parties
from fastapi import FastAPI
from pydantic import BaseModel
from starlette.responses import Response

from pyrun_backend.auto_generated import version
from pyrun_backend.dependencies import dependencies


app: FastAPI = FastAPI(
    title="pyrun_backend",
    root_path=f"http://localhost:{dependencies().yw_port}/backends/pyrun_backend/{version}",
)

global_state = {}


class CodeRequest(BaseModel):
    cellId: str
    fromCellId: str | None
    code: str
    capturedIn: dict[str, Any]
    capturedOut: list[str]


@app.get("/")
async def home():
    # When proxied through py-youwol, this end point is always triggered, when testing weather a backend
    # is listening. The line is `if not self.is_listening():` in `RedirectSwitch`
    return Response(status_code=200)


@app.post("/run")
async def run_code(body: CodeRequest):
    code = body.code

    # Capture the standard output and error
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = mystdout = io.StringIO()
    sys.stderr = mystderr = io.StringIO()

    if not body.fromCellId:
        global_state.clear()

    entering_scope = global_state[body.fromCellId] if body.fromCellId else {}
    try:
        scope = {
            **entering_scope,
            **body.capturedIn
        }
        exec(code, scope)
        global_state[body.cellId] = scope
        output = mystdout.getvalue()
        error = mystderr.getvalue()
        captured_out = {k: scope[k] for k in body.capturedOut if k}
        return {
            "output": output,
            "capturedOut": captured_out,
            "error": error
        }
    except Exception as e:
        # Handle execution errors
        return {"output": "", "error": str(e)}
    finally:
        # Reset standard output and error
        sys.stdout = old_stdout
        sys.stderr = old_stderr