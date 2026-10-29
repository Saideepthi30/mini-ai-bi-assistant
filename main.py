from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from .database import initialise_database, get_connection
from .assistant import answer_question

load_report = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global load_report
    load_report = initialise_database()
    yield

app = FastAPI(
    title="Mini AI Business Intelligence Assistant",
    description="Ask questions about sales data in natural language; answers are backed by SQLite queries.",
    version="1.0.0",
    lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)

@app.get("/api/health")
def health():
    return {"status": "ok", "dataset": load_report}

@app.get("/api/summary")
def summary():
    with get_connection() as conn:
        row = conn.execute("""
            SELECT COUNT(*) AS transactions,
                   ROUND(COALESCE(SUM(revenue), 0), 2) AS total_revenue,
                   COUNT(DISTINCT product) AS products,
                   COUNT(DISTINCT region) AS regions
            FROM sales_transactions
        """).fetchone()
    return dict(row)

@app.post("/api/ask")
def ask(request: AskRequest):
    try:
        result = answer_question(request.question)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result)
        return result
    except HTTPException:
        raise
    except Exception:
        # Avoid exposing internal paths, SQL parameters, or tracebacks to API clients.
        raise HTTPException(status_code=500, detail="The question could not be processed. Check the server logs.")

@app.get("/")
def home():
    return FileResponse("static/index.html")

app.mount("/static", StaticFiles(directory="static"), name="static")
