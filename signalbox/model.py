from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
import math
import os
import tempfile


@dataclass(frozen=True)
class Effect:
    id: str
    name: str
    category: str
    kind: str
    recipe: str
    description: str
    fidelity: str = "model"
    temporal: bool = False
    cost: str = "light"
    asset: str = ""
    tags: str = ""


@dataclass
class Setting:
    enabled: bool = True
    strength: float = 0.5
    locked: bool = False
    asset: str = ""
    start: float = 0.0
    end: float | None = None
    roi: list[float] = field(default_factory=lambda: [0.55, 0.2, 0.25, 0.5])


@dataclass
class Project:
    source: str = ""
    effects: dict[str, Setting] = field(default_factory=dict)
    seed: int = 1967
    width: int = 854
    fps: float = 0.0
    threads: int = 2
    crf: int = 18
    schema: int = 1

    def enabled(self):
        from .catalog import CATALOG
        return [(e, self.effects[e.id]) for e in CATALOG
                if e.id in self.effects and self.effects[e.id].enabled]

    def set(self, effect_id, enabled=True):
        self.effects.setdefault(effect_id, Setting()).enabled = enabled

    def validate(self):
        from .catalog import BY_ID
        if not isinstance(self.source, str):raise ValueError('Source must be a path string')
        if not isinstance(self.width, int) or not isinstance(self.threads, int) or not isinstance(self.crf, int):
            raise ValueError('Width, threads and CRF must be integers')
        if self.schema != 1:
            raise ValueError(f"Unsupported project schema {self.schema}")
        if not 0 <= self.width <= 7680 or (self.width and self.width < 64):
            raise ValueError("Width must be 0 (source) or 64–7680")
        if not math.isfinite(self.fps) or not 0 <= self.fps <= 240:
            raise ValueError("FPS must be 0 (source) or up to 240")
        if not 1 <= self.threads <= 16 or not 0 <= self.crf <= 51:
            raise ValueError("Threads must be 1–16 and CRF 0–51")
        if not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("Seed must be a nonnegative integer")
        for key, s in self.effects.items():
            if not isinstance(s.enabled, bool) or not isinstance(s.locked, bool) or not isinstance(s.asset, str):
                raise ValueError(f'Invalid boolean/path field for {key}')
            if key not in BY_ID:
                raise ValueError(f"Unknown effect: {key}; project requires a newer catalog?")
            if not math.isfinite(s.strength) or not 0 <= s.strength <= 1:
                raise ValueError(f"Invalid strength for {key}")
            if not math.isfinite(s.start) or s.start < 0 or (s.end is not None and
                (not math.isfinite(s.end) or s.end <= s.start)):
                raise ValueError(f"Invalid time window for {key}")
            if len(s.roi) != 4 or any(not math.isfinite(x) or not 0 <= x <= 1 for x in s.roi):
                raise ValueError(f"Invalid region for {key}")
            x,y,w,h = s.roi
            if w <= 0 or h <= 0 or x+w > 1.0001 or y+h > 1.0001:
                raise ValueError(f"Region must fit inside picture for {key}")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        data = dict(data)
        data['effects'] = {k: Setting(**v) for k,v in data.get('effects', {}).items()}
        p = cls(**data)
        p.validate()
        return p

    def save(self, path):
        self.validate()
        path = Path(path).expanduser().resolve()
        if path.suffix.lower() != '.json':raise ValueError('Project files must use the .json extension')
        protected = {Path(v).expanduser().resolve() for v in [self.source, *[s.asset for s in self.effects.values()]] if v}
        if path in protected:raise ValueError('A project cannot overwrite source media or assets')
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.project-', suffix='.json')
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
                f.write('\n')
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)

    @classmethod
    def load(cls, path):
        path = Path(path).resolve()
        p = cls.from_dict(json.loads(path.read_text()))
        if p.source and not Path(p.source).is_absolute(): p.source = str(path.parent / p.source)
        for s in p.effects.values():
            if s.asset and not Path(s.asset).is_absolute(): s.asset = str(path.parent / s.asset)
        return p
