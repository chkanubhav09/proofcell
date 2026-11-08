from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from . import drill
from .models import RunStatus
from .runner import manager

app = FastAPI(title="ProofCell")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


class TaskIn(BaseModel):
    task: str


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/runs/{run_id}", response_class=HTMLResponse)
async def run_page(request: Request, run_id: str):
    run = manager.get(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return templates.TemplateResponse("run.html", {"request": request, "run": run})


@app.post("/api/runs")
async def create_run(body: TaskIn):
    task = body.task.strip()
    if not task or len(task) > 2000:
        raise HTTPException(400, "task must be 1-2000 chars")
    run = manager.start(task)
    return {"run_id": run.id}


@app.get("/api/runs/{run_id}")
async def run_state(run_id: str):
    run = manager.get(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return {
        "id": run.id,
        "task": run.task,
        "status": run.status.value,
        "plan": run.plan.model_dump() if run.plan else None,
        "results": [r.model_dump() for r in run.results],
        "ledger_head": run.ledger.head,
        "ledger_events": len(run.ledger.events),
    }


@app.get("/api/runs/{run_id}/stream")
async def run_stream(run_id: str):
    run = manager.get(run_id)
    if not run:
        raise HTTPException(404, "run not found")

    async def events():
        seen = 0
        while True:
            evs = run.ledger.events
            while seen < len(evs):
                yield f"data: {json.dumps(evs[seen])}\n\n"
                seen += 1
            if run.status in (RunStatus.completed, RunStatus.failed) and seen >= len(evs):
                yield f"data: {json.dumps({'kind': 'end', 'status': run.status.value})}\n\n"
                return
            await asyncio.sleep(0.5)

    return StreamingResponse(events(), media_type="text/event-stream")


@app.post("/api/runs/{run_id}/approve")
async def approve(run_id: str):
    run = manager.get(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    if run.status != RunStatus.awaiting_approval:
        raise HTTPException(409, f"run is {run.status.value}, not awaiting approval")
    run.approve()
    return {"ok": True}


@app.get("/api/drill/scenarios")
async def drill_scenarios():
    return {"scenarios": [{k: s[k] for k in ("id", "title", "task", "expectation")}
                          for s in drill.SCENARIOS]}


@app.post("/api/drill/{scenario_id}")
async def run_drill(scenario_id: str):
    scenario = drill.get(scenario_id)
    if not scenario:
        raise HTTPException(404, "unknown drill scenario")
    run = manager.start(scenario["task"],
                        plan_override=drill.canned_plan_for(scenario["task"]))
    return {"run_id": run.id, "expectation": scenario["expectation"]}


@app.get("/api/runs/{run_id}/ledger")
async def ledger(run_id: str):
    run = manager.get(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return run.ledger.to_dict()


@app.get("/api/runs/{run_id}/verify")
async def verify(run_id: str):
    run = manager.get(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return {"run_id": run_id, "valid": run.verify(), "head": run.ledger.head,
            "events": len(run.ledger.events)}
