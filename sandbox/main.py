"""
FastAPI service that exposes /execute for running code in a sandbox.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from executor import run_with_tests
from tests import UNIT_TESTS
import re

app = FastAPI(title="RLHF Sandbox API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExecuteRequest(BaseModel):
    code: str
    prompt_index: int          # 0-4, maps to which unit test to use
    timeout: Optional[int] = 20


def extract_python_code(raw: str) -> str:
    """Strip markdown code fences if the LLM wrapped the code."""
    # Match ```python ... ``` or ``` ... ```
    match = re.search(r'```(?:python)?\n(.*?)```', raw, re.DOTALL)
    if match:
        return match.group(1).strip()
    return raw.strip()


@app.get("/")
def root():
    return {"message": "RLHF Sandbox is running"}


@app.post("/execute")
def execute_code(req: ExecuteRequest):
    if req.prompt_index not in UNIT_TESTS:
        raise HTTPException(status_code=400, detail=f"No unit tests for prompt_index={req.prompt_index}")

    clean_code = extract_python_code(req.code)
    test_code = UNIT_TESTS[req.prompt_index]

    result = run_with_tests(
        code=clean_code,
        test_code=test_code,
        timeout=req.timeout
    )
    return result


@app.get("/health")
def health():
    return {"status": "ok"}
