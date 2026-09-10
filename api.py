"""FastAPI wrapper -- no business logic lives here, same pattern as the
Philips submission's api.py. Routes are plain `def` (read-only queries
against state the background pipeline maintains); the pipeline itself is
started from the lifespan hook, not a route, since it must run continuously.
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import db
import pipeline

conn = db.init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(pipeline.run_forever(conn))
    yield
    task.cancel()


app = FastAPI(title="Ovnicom Sentinel-DNS API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/alerts")
def list_alerts(limit: int = 50):
    return db.get_recent_alerts(conn, limit)


@app.get("/api/qoe")
def list_qoe():
    return db.get_all_qoe(conn)
