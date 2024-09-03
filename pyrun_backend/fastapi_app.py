# standard library
import functools
import io
from contextlib import redirect_stdout, redirect_stderr
from typing import Any
import time

# third parties
from fastapi import FastAPI
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import Response

from pyrun_backend.auto_generated import version
from pyrun_backend.dependencies import dependencies
from youwol.utils import ContextFactory

app: FastAPI = FastAPI(
    title="pyrun_backend",
    root_path=f"http://localhost:{dependencies().yw_port}/backends/pyrun_backend/{version}",
)


class CodeRequest(BaseModel):
    cellId: str
    code: str
    capturedIn: dict[str, Any]
    capturedOut: list[str]

global_scope = {}

def exec_and_capture_new_vars(code, scope):
    # This function was used to determine which variables were created or modified in a code cell.
    # It turns out that it is not really possible to determine which variables were modified in a code cell.
    # We keep a simple approach here using a single global state.
    exec(code, scope)
    return scope


@app.get("/")
async def home():
    # When proxied through py-youwol, this end point is always triggered, when testing weather a backend
    # is listening. The line is `if not self.is_listening():` in `RedirectSwitch`
    return Response(status_code=200)


@app.post("/run")
async def run_code(request: Request, body: CodeRequest):
    global global_scope

    code = body.code
    async with ContextFactory.proxied_backend_context(request).start(
            action="/run"
    ) as ctx:

        entering_scope = global_scope
        try:
            scope = {
                **entering_scope,
                **body.capturedIn
            }
            await ctx.info("Input scope prepared")

            start = time.time()
            cell_stdout = io.StringIO()
            cell_stderr = io.StringIO()
            with redirect_stdout(cell_stdout), redirect_stderr(cell_stderr):
                print(f"Execute cell {body.cellId}")
                new_scope = exec_and_capture_new_vars(code, scope)

            end = time.time()
            output = cell_stdout.getvalue()
            error = cell_stderr.getvalue()
            await ctx.info(f"'exec(code, scope)' done in {int(1000*(end-start))} ms",
                           data={"output": output, "error": error})
            global_scope = new_scope
            captured_out = {k: new_scope[k] for k in body.capturedOut if k}

            await ctx.info("Output scope persisted")
            return {
                "output": output,
                "capturedOut": captured_out,
                "error": error
            }
        except Exception as e:
            return {"output": "", "error": str(e)}
