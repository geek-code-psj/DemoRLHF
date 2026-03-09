from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import requests
import google.generativeai as genai
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/rlhf")
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Prompt(Base):
    __tablename__ = "prompts"
    id = Column(Integer, primary_key=True)
    text = Column(String)
    prompt_index = Column(Integer, nullable=True)

class Response(Base):
    __tablename__ = "responses"
    id = Column(Integer, primary_key=True)
    prompt_id = Column(Integer)
    model_name = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

PROMPTS = [
    "Write a Python script using asyncio and aiohttp to fetch data from 1,000 different API endpoints concurrently. The target API has a strict rate limit of 50 requests per second. You must implement a token bucket algorithm for rate limiting, and an exponential backoff mechanism with jitter for handling HTTP 429 (Too Many Requests) errors.",
    "Write a Python function using pandas or standard libraries to process a 50GB CSV file of user transactions. The function must calculate the total transaction volume per user and output the top 100 users by volume to a new JSON file. You have a strict memory limit of 2GB RAM. Do not load the entire file into memory at once.",
    "Implement a thread-safe In-Memory Cache class in Python. It must support an LRU (Least Recently Used) eviction policy and a TTL (Time-To-Live) expiration for each key. Include a background worker thread that safely purges expired keys every 60 seconds without blocking read/write operations.",
    "Write a Python middleware function for a FastAPI application that acts as a Prompt Injection shield. It must take raw user input, sanitize it to remove common jailbreak patterns (like 'ignore previous instructions'), detect hidden system commands, and return a clean string. If malicious intent is detected with high confidence, raise an HTTP 400 error.",
    "Create a custom Python decorator named @robust_retry. It should attempt to execute the wrapped function up to 3 times if an exception occurs. If it fails on the 3rd try, it must log the full stack trace to a file named error_log.txt and send a mock email alert. The decorator must strictly preserve the original function's name and docstring using functools.wraps."
]


def generate_responses_task():
    db = SessionLocal()
    Base.metadata.create_all(bind=engine)

    # Seed prompts if empty
    if db.query(Prompt).count() == 0:
        for i, text in enumerate(PROMPTS):
            db.add(Prompt(text=text, prompt_index=i))
        db.commit()
        print(f"Seeded {len(PROMPTS)} prompts.")

    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
    else:
        print("No GEMINI_API_KEY found. Using mock responses.")

    prompts = db.query(Prompt).all()
    for prompt in prompts:
        existing = db.query(Response).filter(Response.prompt_id == prompt.id).count()
        if existing >= 2:
            continue

        for i in range(2):
            model_name = f"gemini-pro-attempt-{i+1}"
            # Vary temperature by attempting rephrasing
            prefix = "" if i == 0 else "Provide a concise, optimized solution: "

            if api_key:
                try:
                    resp = model.generate_content(f"{prefix}{prompt.text}")
                    content = resp.text
                except Exception as e:
                    content = f"# Error generating response: {str(e)}"
            else:
                content = f"# Mock response {i+1} for prompt {prompt.id}\ndef solution():\n    pass"

            db.add(Response(prompt_id=prompt.id, model_name=model_name, content=content))

    db.commit()
    db.close()
    print("Generation complete.")


def execute_responses_task():
    """Call the backend /execute endpoint for every response without a result."""
    db = SessionLocal()
    responses = db.query(Response).all()
    db.close()

    for resp in responses:
        try:
            result = requests.post(
                f"{BACKEND_URL}/execute/{resp.id}",
                timeout=35
            )
            if result.status_code == 200:
                print(f"Executed response {resp.id}: {result.json()}")
            else:
                print(f"Sandbox error for response {resp.id}: {result.text}")
        except Exception as e:
            print(f"Failed to execute response {resp.id}: {e}")


default_args = {
    'owner': 'ethara',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'rlhf_generator_dag',
    default_args=default_args,
    description='Generate and evaluate code responses for RLHF',
    schedule_interval=timedelta(days=1),
    catchup=False,
) as dag:

    generate_task = PythonOperator(
        task_id='generate_llm_responses',
        python_callable=generate_responses_task,
    )

    execute_task = PythonOperator(
        task_id='execute_and_test_responses',
        python_callable=execute_responses_task,
    )

    generate_task >> execute_task
