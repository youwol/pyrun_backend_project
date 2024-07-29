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

global_state = {}


class CodeRequest(BaseModel):
    cellId: str
    previousCellIds: list[str]
    code: str
    capturedIn: dict[str, Any]
    capturedOut: list[str]


def exec_and_capture_new_vars(code, scope):
    initial_keys = set(scope.keys())
    exec(code, scope)
    final_keys = set(scope.keys())
    new_keys = final_keys - initial_keys
    new_scope = {k: scope[k] for k in new_keys}
    return new_scope


@app.get("/")
async def home():
    # When proxied through py-youwol, this end point is always triggered, when testing weather a backend
    # is listening. The line is `if not self.is_listening():` in `RedirectSwitch`
    return Response(status_code=200)


@app.post("/run")
async def run_code(request: Request, body: CodeRequest):
    code = body.code
    async with ContextFactory.proxied_backend_context(request).start(
            action="/run"
    ) as ctx:

        if not body.previousCellIds:
            global_state.clear()

        # It may happen that the scope associated with `body.previousCellIds` is not yet available
        # from some cell (e.g. for reactive cells).
        # If the currently executed cell references a symbol from it, it will raise an exception.
        # However, if the previous cell has finished execution, it will be OK.
        # It is the responsibility of the consumer to ensure that the previous cell has finished if a symbol
        # from it is used in the current cell.

        entering_scope = functools.reduce(lambda acc, e: {**acc, **global_state.get(e, {})}, body.previousCellIds, {})
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
            global_state[body.cellId] = new_scope
            captured_out = {k: new_scope[k] for k in body.capturedOut if k}

            await ctx.info("Output scope persisted")
            return {
                "output": output,
                "capturedOut": captured_out,
                "error": error
            }
        except Exception as e:
            return {"output": "", "error": str(e)}
