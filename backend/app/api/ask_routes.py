from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.qa import router as qa
from app.qa.schemas import AskRequest, AskResponse, AskStatus

router = APIRouter(prefix="/api/ask", tags=["ask"])


@router.get("/status", response_model=AskStatus)
def status() -> AskStatus:
    return qa.status()


@router.post("", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    try:
        return await run_in_threadpool(qa.answer, req)
    except (RuntimeError, FileNotFoundError) as exc:  # missing key/model or a failed upstream call: tell the user why
        raise HTTPException(status_code=503, detail=str(exc)) from exc
