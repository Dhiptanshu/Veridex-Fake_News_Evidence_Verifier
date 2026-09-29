from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.pipeline.orchestrator import run_pipeline
from app.schemas.pipeline import PipelineEvent, StageInfo, VerifyRequest
from app.stages import list_stages

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/stages", response_model=list[StageInfo])
def stages() -> list[StageInfo]:
    return list_stages()


@router.post("/verify", response_model=list[PipelineEvent])
async def verify(req: VerifyRequest) -> list[PipelineEvent]:
    return [ev async for ev in run_pipeline(req)]


@router.post("/verify/stream")
async def verify_stream(req: VerifyRequest) -> StreamingResponse:
    """Server-sent events: one `data:` line of PipelineEvent JSON per event."""

    async def gen() -> AsyncIterator[str]:
        async for ev in run_pipeline(req):
            yield f"data: {ev.model_dump_json()}\n\n"

    return StreamingResponse(
        gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
