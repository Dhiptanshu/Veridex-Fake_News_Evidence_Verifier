from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar

from pydantic import BaseModel

from app.schemas.pipeline import SLOTS, StageInfo


@dataclass
class StageContext:
    """Everything a stage may read: the claim plus outputs of earlier slots."""

    claim: str
    results: dict[str, BaseModel] = field(default_factory=dict)


class Stage(ABC):
    """A single implementation of a pipeline slot. Subclass, set the class vars, and @register it."""

    slot: ClassVar[str]
    name: ClassVar[str]
    label: ClassVar[str]
    description: ClassVar[str] = ""
    family: ClassVar[str] = "classical"
    default: ClassVar[bool] = False
    placeholder: ClassVar[bool] = False

    @abstractmethod
    async def run(self, ctx: StageContext) -> BaseModel: ...


_REGISTRY: dict[str, dict[str, type[Stage]]] = {slot: {} for slot in SLOTS}


def register(cls: type[Stage]) -> type[Stage]:
    if cls.slot not in _REGISTRY:
        raise ValueError(f"Unknown slot {cls.slot!r}; expected one of {SLOTS}")
    if cls.name in _REGISTRY[cls.slot]:
        raise ValueError(f"Duplicate stage {cls.slot}/{cls.name}")
    _REGISTRY[cls.slot][cls.name] = cls
    return cls


def get_stage(slot: str, name: str | None = None) -> Stage:
    impls = _REGISTRY[slot]
    if name is None:
        defaults = [c for c in impls.values() if c.default]
        if not defaults:
            raise LookupError(f"No default stage registered for slot {slot!r}")
        return defaults[-1]()
    if name not in impls:
        raise LookupError(f"Unknown stage {slot}/{name}; available: {sorted(impls)}")
    return impls[name]()


def list_stages() -> list[StageInfo]:
    return [
        StageInfo(
            slot=slot, name=c.name, label=c.label, description=c.description,
            family=c.family, is_default=c.default, placeholder=c.placeholder,  # type: ignore[arg-type]
        )
        for slot in SLOTS
        for c in _REGISTRY[slot].values()
    ]
