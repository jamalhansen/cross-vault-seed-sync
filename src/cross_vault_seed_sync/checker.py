"""Verify the Contexta seed-promotion handoff into BrainSync.

Read-only, per the spec at BrainSync's knowledge/tools/03-cross-vault-seed-
sync.md -- pure filesystem + frontmatter checks, no LLM, no writes. A seed
gets `status: promoted` and `promoted_to: <path>`; nothing previously
verified the target actually exists, or that the BrainSync file at that
target points back via `source_note`.
"""
import os
from dataclasses import dataclass
from pathlib import Path

import frontmatter


@dataclass
class PromotedSeed:
    path: Path
    promoted_to: str

    @property
    def slug(self) -> str:
        return self.path.stem


@dataclass
class SourceNoteRef:
    path: Path
    source_note: str


@dataclass
class CheckResult:
    kind: str  # "ok" | "miss" | "orphan"
    seed_path: Path | None
    brainsync_path: Path | None
    detail: str


def _load(path: Path, on_error=None):
    try:
        return frontmatter.load(path)
    except Exception as e:  # noqa: BLE001
        if on_error:
            on_error(path, e)
        return None


def resolve_target(raw: str) -> Path:
    """Expand ~ and strip the quoting some promoted_to values carry."""
    cleaned = raw.strip().strip("'\"")
    return Path(os.path.expanduser(cleaned))


def scan_promoted_seeds(seeds_dir: Path, on_error=None) -> list[PromotedSeed]:
    """Every Contexta seed with status: promoted and a non-empty promoted_to."""
    if not seeds_dir.exists():
        return []

    seeds = []
    for path in sorted(seeds_dir.glob("*.md")):
        post = _load(path, on_error)
        if post is None:
            continue
        if post.get("status") != "promoted":
            continue
        promoted_to = post.get("promoted_to")
        if not promoted_to or not str(promoted_to).strip():
            continue
        seeds.append(PromotedSeed(path=path, promoted_to=str(promoted_to)))
    return seeds


def scan_source_note_refs(brainsync_dir: Path, on_error=None) -> list[SourceNoteRef]:
    """Every BrainSync markdown file with a non-empty source_note field."""
    if not brainsync_dir.exists():
        return []

    refs = []
    for path in sorted(brainsync_dir.rglob("*.md")):
        if ".obsidian" in path.parts:
            continue
        post = _load(path, on_error)
        if post is None:
            continue
        source_note = post.get("source_note")
        if source_note and str(source_note).strip():
            refs.append(SourceNoteRef(path=path, source_note=str(source_note)))
    return refs


def check_promoted_targets(seeds: list[PromotedSeed]) -> list[CheckResult]:
    """OK if promoted_to resolves to a real file, MISS if it doesn't."""
    results = []
    for seed in seeds:
        target = resolve_target(seed.promoted_to)
        if target.exists():
            results.append(
                CheckResult(kind="ok", seed_path=seed.path, brainsync_path=target, detail="")
            )
        else:
            results.append(
                CheckResult(
                    kind="miss",
                    seed_path=seed.path,
                    brainsync_path=None,
                    detail=f"promoted_to path not found: {target}",
                )
            )
    return results


def check_orphans(
    refs: list[SourceNoteRef], notes_dir: Path, seeds_dir: Path
) -> list[CheckResult]:
    """ORPHAN if a BrainSync file's source_note doesn't match a real Contexta note or seed."""
    results = []
    for ref in refs:
        slug = ref.source_note.strip()
        note_path = notes_dir / f"{slug}.md"
        seed_path = seeds_dir / f"{slug}.md"
        if note_path.exists() or seed_path.exists():
            continue
        results.append(
            CheckResult(
                kind="orphan",
                seed_path=None,
                brainsync_path=ref.path,
                detail=f"source_note '{slug}' has no matching Contexta note or seed",
            )
        )
    return results
