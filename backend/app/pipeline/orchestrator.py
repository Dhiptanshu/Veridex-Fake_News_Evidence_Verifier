import time
from collections.abc import AsyncIterator

from pydantic import BaseModel

from app.schemas.pipeline import SLOTS, PipelineEvent, VerifyRequest
from app.stages import StageContext, get_stage


async def run_pipeline(req: VerifyRequest) -> AsyncIterator[PipelineEvent]:
    """Run each slot in order, yielding events so callers can stream progress."""
    try:
        stages = [(slot, get_stage(slot, req.options.get(slot))) for slot in SLOTS]
    except LookupError as exc:
        yield PipelineEvent(type="error", message=str(exc))
        return

    ctx = StageContext(claim=req.claim)
    yield PipelineEvent(type="pipeline_start", payload={"claim": req.claim})
    started = time.perf_counter()
    for slot, stage in stages:
        yield PipelineEvent(type="stage_start", slot=slot, impl=stage.name, placeholder=stage.placeholder)
        t0 = time.perf_counter()
        try:
            out: BaseModel = await stage.run(ctx)
        except Exception as exc:  # a stage failure must not kill the stream silently
            yield PipelineEvent(type="error", slot=slot, impl=stage.name, message=f"{type(exc).__name__}: {exc}")
            return
        ctx.results[slot] = out
        yield PipelineEvent(
            type="stage_end", slot=slot, impl=stage.name, placeholder=stage.placeholder,
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 1), payload=out.model_dump(),
        )
    yield PipelineEvent(type="pipeline_end", elapsed_ms=round((time.perf_counter() - started) * 1000, 1))
