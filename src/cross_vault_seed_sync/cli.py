from pathlib import Path
from typing import Annotated

import typer
from local_first_common.tracking import register_tool, timed_run

from .checker import (
    check_orphans,
    check_promoted_targets,
    scan_promoted_seeds,
    scan_source_note_refs,
)

_TOOL = register_tool("cross-vault-seed-sync")

app = typer.Typer(
    name="cross-vault-seed-sync",
    help="Verify the Contexta <-> BrainSync seed-promotion handoff. Read-only.",
    add_completion=False,
)

_DEFAULT_CONTEXTA_PATH = Path.home() / "vaults" / "Contexta"
_DEFAULT_BRAINSYNC_PATH = Path.home() / "vaults" / "BrainSync"


@app.command()
def check(
    contexta_path: Annotated[Path, typer.Option("--contexta-path")] = _DEFAULT_CONTEXTA_PATH,
    brainsync_path: Annotated[Path, typer.Option("--brainsync-path")] = _DEFAULT_BRAINSYNC_PATH,
):
    """Check promoted-seed targets exist, and BrainSync source_note refs resolve."""
    seeds_dir = contexta_path / "seeds"
    notes_dir = contexta_path / "notes"

    def _warn(path: Path, error: Exception) -> None:
        typer.echo(f"  [skipped] {path}: {error}", err=True)

    with timed_run("cross-vault-seed-sync", None, source_location=str(contexta_path)) as run:
        seeds = scan_promoted_seeds(seeds_dir, on_error=_warn)
        refs = scan_source_note_refs(brainsync_path, on_error=_warn)

        target_results = check_promoted_targets(seeds)
        orphan_results = check_orphans(refs, notes_dir, seeds_dir)
        run.item_count = len(seeds) + len(refs)

    ok = [r for r in target_results if r.kind == "ok"]
    miss = [r for r in target_results if r.kind == "miss"]

    for r in ok:
        typer.echo(f"OK     {r.seed_path.name} -> {r.brainsync_path}")
    for r in miss:
        typer.echo(f"MISS   {r.seed_path.name}: {r.detail}")
    for r in orphan_results:
        typer.echo(f"ORPHAN {r.brainsync_path}: {r.detail}")

    typer.echo(
        f"\n{len(ok)} ok, {len(miss)} miss, {len(orphan_results)} orphan"
        f" ({len(seeds)} promoted seed(s), {len(refs)} source_note reference(s) checked)"
    )

    if miss or orphan_results:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
