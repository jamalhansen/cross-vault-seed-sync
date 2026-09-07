from pathlib import Path

from typer.testing import CliRunner

from cross_vault_seed_sync.cli import app

runner = CliRunner()


def _write(path: Path, frontmatter: dict, body: str = "body\n") -> None:
    lines = ["---"]
    for k, v in frontmatter.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append(body)
    path.write_text("\n".join(lines))


class TestCheckCommand:
    def test_all_ok_exits_zero(self, tmp_path):
        contexta = tmp_path / "Contexta"
        brainsync = tmp_path / "BrainSync"
        (contexta / "seeds").mkdir(parents=True)
        (contexta / "notes").mkdir(parents=True)
        brainsync.mkdir()

        target = brainsync / "post.md"
        _write(target, {"source_note": "s1"})
        _write(contexta / "seeds" / "s1.md", {"status": "promoted", "promoted_to": str(target)})

        result = runner.invoke(
            app, ["--contexta-path", str(contexta), "--brainsync-path", str(brainsync)]
        )
        assert result.exit_code == 0
        assert "OK" in result.output
        assert "0 miss, 0 orphan" in result.output

    def test_miss_and_orphan_exit_nonzero(self, tmp_path):
        contexta = tmp_path / "Contexta"
        brainsync = tmp_path / "BrainSync"
        (contexta / "seeds").mkdir(parents=True)
        (contexta / "notes").mkdir(parents=True)
        brainsync.mkdir()

        _write(
            contexta / "seeds" / "s1.md",
            {"status": "promoted", "promoted_to": str(tmp_path / "does-not-exist.md")},
        )
        _write(brainsync / "orphan-post.md", {"source_note": "ghost"})

        result = runner.invoke(
            app, ["--contexta-path", str(contexta), "--brainsync-path", str(brainsync)]
        )
        assert result.exit_code == 1
        assert "MISS" in result.output
        assert "ORPHAN" in result.output
