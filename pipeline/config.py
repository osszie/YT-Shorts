"""Configuration loader.

Everything that makes the pipeline niche-agnostic lives in config/*.yaml:
  - niches/<id>.yaml  : the topic source, which lenses/formats/voices it uses
  - lenses.yaml       : the angle lenses (the "take" menu)
  - formats.yaml      : structural skeletons rotated per video
  - surface.yaml      : voices / caption styles / intro styles to rotate

A Config bundles a resolved niche together with the shared banks so stages never
have to touch YAML directly.
"""
from __future__ import annotations

import os
import pathlib
from dataclasses import dataclass
from typing import Any

import yaml

from . import ROOT

CONFIG_DIR = ROOT / "config"
DEFAULT_NICHE = os.getenv("NICHE", "hidden_things")


def _load_yaml(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing config file: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass
class Config:
    niche: dict[str, Any]
    lenses: dict[str, Any]
    formats: dict[str, Any]
    surface: dict[str, Any]

    # --- niche convenience accessors -------------------------------------
    @property
    def niche_id(self) -> str:
        return self.niche["id"]

    @property
    def lens_ids(self) -> list[str]:
        return list(self.niche.get("lenses", list(self.lenses.keys())))

    @property
    def format_ids(self) -> list[str]:
        return list(self.niche.get("formats", list(self.formats.keys())))

    def lens(self, lens_id: str) -> dict[str, Any]:
        return self.lenses[lens_id]

    def fmt(self, format_id: str) -> dict[str, Any]:
        return self.formats[format_id]

    # --- surface banks, filtered to what the niche opts into -------------
    def voices(self) -> list[dict[str, Any]]:
        wanted = self.niche.get("surface", {}).get("voices")
        allv = self.surface.get("voices", [])
        if not wanted:
            return allv
        return [v for v in allv if v["id"] in wanted] or allv

    def caption_styles(self) -> list[dict[str, Any]]:
        wanted = self.niche.get("surface", {}).get("caption_styles")
        alls = self.surface.get("caption_styles", [])
        if not wanted:
            return alls
        return [s for s in alls if s["id"] in wanted] or alls

    def intro_styles(self) -> list[dict[str, Any]]:
        wanted = self.niche.get("surface", {}).get("intro_styles")
        alli = self.surface.get("intro_styles", [])
        if not wanted:
            return alli
        return [i for i in alli if i["id"] in wanted] or alli


def list_niches() -> list[str]:
    niche_dir = CONFIG_DIR / "niches"
    return sorted(p.stem for p in niche_dir.glob("*.yaml"))


def load_config(niche_id: str | None = None) -> Config:
    niche_id = niche_id or DEFAULT_NICHE
    niche_path = CONFIG_DIR / "niches" / f"{niche_id}.yaml"
    if not niche_path.exists():
        available = ", ".join(list_niches())
        raise ValueError(f"Unknown niche '{niche_id}'. Available: {available}")
    return Config(
        niche=_load_yaml(niche_path),
        lenses=_load_yaml(CONFIG_DIR / "lenses.yaml").get("lenses", {}),
        formats=_load_yaml(CONFIG_DIR / "formats.yaml").get("formats", {}),
        surface=_load_yaml(CONFIG_DIR / "surface.yaml"),
    )
