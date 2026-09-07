from pathlib import Path

from cross_vault_seed_sync.checker import (
    check_orphans,
    check_promoted_targets,
    resolve_target,
    scan_promoted_seeds,
    scan_source_note_refs,
)


def _write(path: Path, frontmatter: dict, body: str = "body\n") -> None:
    lines = ["---"]
    for k, v in frontmatter.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append(body)
    path.write_text("\n".join(lines))


class TestResolveTarget:
    def test_expands_home(self):
        result = resolve_target("~/vaults/BrainSync/x.md")
        assert str(result).startswith(str(Path.home()))
        assert not str(result).startswith("~")

    def test_strips_quotes(self):
        result = resolve_target('"~/vaults/BrainSync/x.md"')
        assert "\"" not in str(result)

    def test_strips_whitespace(self):
        result = resolve_target("  ~/x.md  ")
        assert str(result) == str(Path.home() / "x.md")


class TestScanPromotedSeeds:
    def test_finds_promoted_with_target(self, tmp_path):
        d = tmp_path / "seeds"
        d.mkdir()
        _write(d / "s1.md", {"status": "promoted", "promoted_to": "~/x.md"})
        result = scan_promoted_seeds(d)
        assert len(result) == 1
        assert result[0].slug == "s1"

    def test_skips_non_promoted(self, tmp_path):
        d = tmp_path / "seeds"
        d.mkdir()
        _write(d / "s1.md", {"status": "seed"})
        _write(d / "s2.md", {"status": "developing"})
        assert scan_promoted_seeds(d) == []

    def test_skips_promoted_with_empty_target(self, tmp_path):
        d = tmp_path / "seeds"
        d.mkdir()
        _write(d / "s1.md", {"status": "seed", "promoted_to": ""})
        assert scan_promoted_seeds(d) == []

    def test_missing_dir_returns_empty(self, tmp_path):
        assert scan_promoted_seeds(tmp_path / "nope") == []

    def test_malformed_frontmatter_skipped_not_fatal(self, tmp_path):
        d = tmp_path / "seeds"
        d.mkdir()
        (d / "bad.md").write_text('---\ntitle: "Quoted" trailing breaks yaml\n---\nbody\n')
        _write(d / "good.md", {"status": "promoted", "promoted_to": "~/x.md"})
        errors = []
        result = scan_promoted_seeds(d, on_error=lambda p, e: errors.append(p.name))
        assert [s.slug for s in result] == ["good"]
        assert errors == ["bad.md"]


class TestScanSourceNoteRefs:
    def test_finds_files_with_source_note(self, tmp_path):
        d = tmp_path / "brainsync"
        d.mkdir()
        _write(d / "post.md", {"source_note": "some-note-slug"})
        result = scan_source_note_refs(d)
        assert len(result) == 1
        assert result[0].source_note == "some-note-slug"

    def test_skips_files_without_source_note(self, tmp_path):
        d = tmp_path / "brainsync"
        d.mkdir()
        _write(d / "post.md", {"title": "no source note here"})
        assert scan_source_note_refs(d) == []

    def test_skips_obsidian_directory(self, tmp_path):
        d = tmp_path / "brainsync" / ".obsidian" / "plugins"
        d.mkdir(parents=True)
        _write(d / "data.md", {"source_note": "shouldnt-be-found"})
        assert scan_source_note_refs(tmp_path / "brainsync") == []

    def test_recurses_subdirectories(self, tmp_path):
        d = tmp_path / "brainsync" / "blog" / "series" / "foo"
        d.mkdir(parents=True)
        _write(d / "post.md", {"source_note": "deep-note"})
        result = scan_source_note_refs(tmp_path / "brainsync")
        assert len(result) == 1


class TestCheckPromotedTargets:
    def test_ok_when_target_exists(self, tmp_path):
        target = tmp_path / "real.md"
        target.write_text("exists")
        from cross_vault_seed_sync.checker import PromotedSeed

        seed = PromotedSeed(path=Path("s1.md"), promoted_to=str(target))
        results = check_promoted_targets([seed])
        assert results[0].kind == "ok"

    def test_miss_when_target_missing(self, tmp_path):
        from cross_vault_seed_sync.checker import PromotedSeed

        seed = PromotedSeed(path=Path("s1.md"), promoted_to=str(tmp_path / "nope.md"))
        results = check_promoted_targets([seed])
        assert results[0].kind == "miss"
        assert "not found" in results[0].detail


class TestCheckOrphans:
    def test_no_orphan_when_note_exists(self, tmp_path):
        notes_dir = tmp_path / "notes"
        seeds_dir = tmp_path / "seeds"
        notes_dir.mkdir()
        seeds_dir.mkdir()
        (notes_dir / "real-note.md").write_text("x")
        from cross_vault_seed_sync.checker import SourceNoteRef

        ref = SourceNoteRef(path=Path("post.md"), source_note="real-note")
        assert check_orphans([ref], notes_dir, seeds_dir) == []

    def test_no_orphan_when_seed_exists(self, tmp_path):
        notes_dir = tmp_path / "notes"
        seeds_dir = tmp_path / "seeds"
        notes_dir.mkdir()
        seeds_dir.mkdir()
        (seeds_dir / "real-seed.md").write_text("x")
        from cross_vault_seed_sync.checker import SourceNoteRef

        ref = SourceNoteRef(path=Path("post.md"), source_note="real-seed")
        assert check_orphans([ref], notes_dir, seeds_dir) == []

    def test_orphan_when_neither_exists(self, tmp_path):
        notes_dir = tmp_path / "notes"
        seeds_dir = tmp_path / "seeds"
        notes_dir.mkdir()
        seeds_dir.mkdir()
        from cross_vault_seed_sync.checker import SourceNoteRef

        ref = SourceNoteRef(path=Path("post.md"), source_note="ghost-slug")
        results = check_orphans([ref], notes_dir, seeds_dir)
        assert len(results) == 1
        assert results[0].kind == "orphan"
