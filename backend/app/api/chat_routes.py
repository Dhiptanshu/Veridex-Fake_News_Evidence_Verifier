import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.assistant import agent, tools
from app.assistant.schemas import ChatRequest, ChatStatus
from app.core.config import settings
from app.llm import client

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/status", response_model=ChatStatus)
def status() -> ChatStatus:
    return ChatStatus(configured=client.configured(), model=settings.aicredits_model, tools=tools.TOOL_NAMES)


@router.post("")
def chat(req: ChatRequest) -> StreamingResponse:
    """Server-sent events: tool, tool_done, sources, token, done | error. The generator is synchronous (blocking HTTP to the
    LLM and news APIs), so Starlette runs it in a worker thread."""

    def events():
        try:
            for ev in agent.run(req):
                yield f"data: {json.dumps(ev)}\n\n"
        except Exception as exc:  # noqa: BLE001  a crash must reach the UI as an event, not a dropped connection
            yield f"data: {json.dumps({'type': 'error', 'message': f'{type(exc).__name__}: {exc}'})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
