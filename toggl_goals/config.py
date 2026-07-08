import yaml
from dataclasses import dataclass, field
from typing import List, Dict
from pathlib import Path

@dataclass
class Goal:
    name: str
    target_mins: int
    tier: str
    keywords: List[str] = field(default_factory=list)
    icon: str = ""
    color: str = "#666"
    type: str = "maximize"        # "maximize" or "minimize"
    cap_mins: int = 0             # used by minimize goals (max allowed before score=0)

    @property
    def is_minimize(self) -> bool:
        return self.type == "minimize"

    @property
    def threshold_mins(self) -> int:
        """target_mins for maximize goals, cap_mins for minimize goals."""
        return self.cap_mins if self.is_minimize else self.target_mins

class Config:
    def __init__(self, path: str = None):
        if path is None:
            path = Path(__file__).parent.parent / "config" / "goals.yaml"
        self._raw = yaml.safe_load(open(path))

    @property
    def goals(self) -> Dict[str, Goal]:
        goals = {}
        for name, cfg in self._raw["goals"].items():
            goals[name] = Goal(
                name=name,
                target_mins=cfg.get("target_mins", cfg.get("cap_mins", 0)),
                tier=cfg["tier"],
                keywords=[k.lower() for k in cfg.get("keywords", [])],
                icon=cfg.get("icon", ""),
                color=cfg.get("color", "#666"),
                type=cfg.get("type", "maximize"),
                cap_mins=cfg.get("cap_mins", 0),
            )
        return goals

    @property
    def maintenance_keywords(self) -> List[str]:
        return [k.lower() for k in self._raw.get("maintenance_keywords", [])]

    @property
    def tax_keywords(self) -> List[str]:
        return [k.lower() for k in self._raw.get("tax_keywords", [])]

    @property
    def non_negotiables(self) -> List[str]:
        return [n for n, g in self.goals.items() if g.tier == "non-negotiable"]

    @property
    def high_ideals(self) -> List[str]:
        return [n for n, g in self.goals.items() if g.tier == "high-ideal"]
