from fastapi import FastAPI, Depends, HTTPException, Body
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import models
import httpx
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os

SANDBOX_URL = os.getenv("SANDBOX_URL", "http://sandbox:8001")

app = FastAPI(title="RLHF Dashboard API")

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
    response_id: int
    stdout: Optional[str]
    stderr: Optional[str]
    exit_code: Optional[int]
    tests_passed: int
    tests_failed: int
    tests_error: int
    timed_out: bool

    class Config:
        from_attributes = True

class ResponseSchema(BaseModel):
    id: int
    prompt_id: int
    model_name: str
    content: str
    execution_result: Optional[ExecutionResultSchema] = None

    class Config:
        from_attributes = True

class PromptSchema(BaseModel):
    id: int
    text: str
    prompt_index: Optional[int] = None
    responses: List[ResponseSchema]

    class Config:
        from_attributes = True

class PromptCreate(BaseModel):
    text: str

class RatingCreate(BaseModel):
    response_id: int
    score: int
    comment: Optional[str] = None

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
    return {"message": "RLHF API is running"}

@app.get("/prompts/next", response_model=Optional[PromptSchema])
def get_next_prompt(db: Session = Depends(get_db)):
    # Get a prompt that has responses but where not all responses have been rated
    prompts = db.query(models.Prompt).options(joinedload(models.Prompt.responses)).all()
    for prompt in prompts:
        rated_response_ids = {r.response_id for r in db.query(models.Rating).all()}
        unrated_responses = [resp for resp in prompt.responses if resp.id not in rated_response_ids]
        if unrated_responses:
            return prompt
    return None

@app.get("/prompts", response_model=List[PromptSchema])
def get_all_prompts(db: Session = Depends(get_db)):
    return db.query(models.Prompt).options(
        joinedload(models.Prompt.responses).joinedload(models.Response.execution_result)
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

@app.post("/ratings")
def create_rating(rating: RatingCreate, db: Session = Depends(get_db)):
    db_rating = models.Rating(
        response_id=rating.response_id,
        score=rating.score,
        comment=rating.comment
    )
    db.add(db_rating)
    db.commit()
    db.refresh(db_rating)
    return {"status": "success", "id": db_rating.id}

@app.post("/execute/{response_id}")
def execute_response(response_id: int, db: Session = Depends(get_db)):
    """Trigger sandbox execution for a given response."""
    resp = db.query(models.Response).filter(models.Response.id == response_id).first()
    if not resp:
        raise HTTPException(status_code=404, detail="Response not found")

    prompt = db.query(models.Prompt).filter(models.Prompt.id == resp.prompt_id).first()
    prompt_index = prompt.prompt_index if prompt and prompt.prompt_index is not None else 0

    try:
        sandbox_resp = httpx.post(
            f"{SANDBOX_URL}/execute",
            json={"code": resp.content, "prompt_index": prompt_index},
            timeout=30
        )
        result_data = sandbox_resp.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sandbox unavailable: {str(e)}")

    # Upsert ExecutionResult
    existing = db.query(models.ExecutionResult).filter(
        models.ExecutionResult.response_id == response_id
    ).first()

    if existing:
        for k, v in result_data.items():
            setattr(existing, k, v)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        ex_result = models.ExecutionResult(response_id=response_id, **result_data)
        db.add(ex_result)
        db.commit()
        db.refresh(ex_result)
        return ex_result

@app.get("/results/{response_id}", response_model=Optional[ExecutionResultSchema])
def get_result(response_id: int, db: Session = Depends(get_db)):
    return db.query(models.ExecutionResult).filter(
        models.ExecutionResult.response_id == response_id
    ).first()

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total_prompts = db.query(models.Prompt).count()
    total_ratings = db.query(models.Rating).count()
    total_executions = db.query(models.ExecutionResult).count()
    return {
        "total_prompts": total_prompts,
        "total_ratings": total_ratings,
        "total_executions": total_executions
    }
