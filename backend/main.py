from fastapi import FastAPI, Depends, HTTPException, Body
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import models
import httpx
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os

SANDBOX_URL = os.getenv("SANDBOX_URL", "http://sandbox:8001")

app = FastAPI(title="Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pydantic schemas ──────────────────────────────────────────────────────────

class ExecutionResultSchema(BaseModel):
    id: int
    prompt_id: int
    stdout: Optional[str]
    stderr: Optional[str]
    exit_code: Optional[int]
    tests_passed: int
    tests_failed: int
    tests_error: int
    timed_out: bool

    class Config:
        from_attributes = True

class PromptSchema(BaseModel):
    id: int
    text: str
    prompt_index: Optional[int] = None
    execution_result: Optional[ExecutionResultSchema] = None

    class Config:
        from_attributes = True

class PromptCreate(BaseModel):
    text: str

# ── DB dependency ─────────────────────────────────────────────────────────────

def get_db():
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    models.init_db()

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
def read_root():
    return {"message": "API is running"}

@app.get("/prompts", response_model=List[PromptSchema])
def get_all_prompts(db: Session = Depends(get_db)):
    return db.query(models.Prompt).options(
        joinedload(models.Prompt.execution_result)
    ).order_by(models.Prompt.id.desc()).all()

@app.post("/prompts", response_model=PromptSchema)
def create_prompt(prompt: PromptCreate, db: Session = Depends(get_db)):
    db_prompt = models.Prompt(text=prompt.text)
    db.add(db_prompt)
    db.commit()
    db.refresh(db_prompt)
    return db_prompt

@app.delete("/prompts/{prompt_id}")
def delete_prompt(prompt_id: int, db: Session = Depends(get_db)):
    prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    db.delete(prompt)
    db.commit()
    return {"status": "success", "message": f"Prompt {prompt_id} deleted"}

@app.post("/execute/{prompt_id}")
def execute_prompt(prompt_id: int, db: Session = Depends(get_db)):
    """Trigger sandbox execution for a given prompt."""
    prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    prompt_index = prompt.prompt_index if prompt and prompt.prompt_index is not None else 0

    try:
        sandbox_resp = httpx.post(
            f"{SANDBOX_URL}/execute",
            json={"code": prompt.text, "prompt_index": prompt_index},
            timeout=30
        )
        result_data = sandbox_resp.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sandbox unavailable: {str(e)}")

    # Upsert ExecutionResult
    existing = db.query(models.ExecutionResult).filter(
        models.ExecutionResult.prompt_id == prompt_id
    ).first()

    if existing:
        for k, v in result_data.items():
            setattr(existing, k, v)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        ex_result = models.ExecutionResult(prompt_id=prompt_id, **result_data)
        db.add(ex_result)
        db.commit()
        db.refresh(ex_result)
        return ex_result

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total_prompts = db.query(models.Prompt).count()
    total_executions = db.query(models.ExecutionResult).count()
    return {
        "total_prompts": total_prompts,
        "total_executions": total_executions
    }
