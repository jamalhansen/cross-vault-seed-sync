# cross-vault-seed-sync

Verifies the Contexta seed-promotion handoff into BrainSync. Read-only.

Built from the spec at `~/vaults/BrainSync/projects/knowledge/tools/03-cross-vault-seed-sync.md`.

## Install

```bash
uv tool install /path/to/cross-vault-seed-sync
```

## Usage

```bash
seed-sync --contexta-path ~/vaults/Contexta --brainsync-path ~/vaults/BrainSync
```

Checks two directions:
1. Every Contexta seed with `status: promoted` -- does its `promoted_to` path exist?
2. Every BrainSync markdown file with `source_note` set -- does that slug match a real Contexta note or seed?

Prints `OK` / `MISS` / `ORPHAN` lines and a summary count. Exits non-zero if
anything is missing or orphaned. Writes nothing -- fixing a mismatch is a
manual follow-up.
