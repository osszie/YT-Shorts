"""Metadata stage — title / description / hashtags / tags.

Honest, specific SEO that matches the video's actual angle (no Reddit-style
clickbait template). Uses the LLM when available, otherwise a clean template
built from the subject + angle. Stored on the job and consumed by the publish
gate preview and the upload stage.
"""
from __future__ import annotations

import re

from .. import llm
from ..config import Config
from ..job import Job
from .base import Stage


def _slug_tags(text: str, limit: int = 8) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9]+", text.lower())
    stop = {"the", "and", "for", "with", "this", "that", "what", "why", "how", "you", "your", "about"}
    seen, tags = set(), []
    for w in words:
        if w in stop or len(w) < 4 or w in seen:
            continue
        seen.add(w)
        tags.append(w)
        if len(tags) >= limit:
            break
    return tags


class MetadataStage(Stage):
    name = "metadata"

    def done(self, job: Job) -> bool:
        return bool(job.data.get("metadata"))

    def run(self, job: Job, cfg: Config) -> None:
        subject = job.data["subject"]
        angle = job.data["angle"]
        base_tags = cfg.niche.get("metadata", {}).get("base_hashtags", ["#shorts"])
        category_id = str(cfg.niche.get("metadata", {}).get("category_id", "27"))

        title, description = "", ""
        if llm.available():
            prompt = (
                f"Subject: {subject}\nAngle: {angle}\n\n"
                "Write YouTube Shorts metadata that honestly matches this video (no clickbait "
                "that the video doesn't pay off).\n"
                "- title: <= 70 chars, curiosity-driven but accurate\n"
                "- description: 1-2 sentences, then a question inviting comments\n"
                'Return JSON: {"title": "...", "description": "..."}'
            )
            try:
                out = llm.generate_json(prompt)
                title = (out.get("title") or "").strip()
                description = (out.get("description") or "").strip()
            except Exception as e:
                job.log(self.name, f"llm metadata failed ({e}); using template")

        if not title:
            title = f"The hidden truth about {subject}"[:70]
        if not description:
            description = f"{angle} What everyday thing should I explain next?"

        hashtags = " ".join(dict.fromkeys(base_tags))  # de-dupe, keep order
        description = f"{description}\n\n{hashtags}"
        tags = [t.lstrip("#") for t in base_tags] + _slug_tags(f"{subject} {title}")

        job.data["metadata"] = {
            "title": title[:100],
            "description": description,
            "tags": list(dict.fromkeys(tags))[:15],
            "category_id": category_id,
        }
        job.mark_stage(self.name, f"title='{title}'")
