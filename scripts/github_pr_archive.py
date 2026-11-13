"""Archive every pull request of this GitHub repository into one Markdown file, before the
repository moves (the PR pages, descriptions and review comments live only on GitHub).

    brew install gh && gh auth login          # once, your own GitHub login
    python scripts/github_pr_archive.py       # -> docs/github_pr_archive.md

Uses the `gh` CLI (`gh api`), so no token is read or stored by this script. For each PR,
oldest first: number, title, author, state, dates, branch -> base, merge commit, the
description, review summaries and every review and conversation comment with its author
and date (code comments with their file and line).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def gh(path: str) -> list:
    out = subprocess.run(["gh", "api", "--paginate", "--slurp", path],
                         capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        sys.exit(f"gh api {path} failed: {out.stderr.strip()}")
    pages = json.loads(out.stdout)
    return [x for page in pages for x in (page if isinstance(page, list) else [page])]


def repo_slug() -> str:
    url = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True,
                         cwd=ROOT, check=True).stdout.strip()
    return url.split("github.com")[-1].lstrip(":/").removesuffix(".git")


def block(text: str | None) -> str:
    text = (text or "").strip()
    return "\n".join("> " + line for line in text.splitlines()) if text else "> (empty)"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "github_pr_archive.md")
    a = ap.parse_args()
    slug = repo_slug()
    prs = sorted(gh(f"repos/{slug}/pulls?state=all&per_page=100"), key=lambda p: p["number"])
    lines = [f"# Pull request archive: `{slug}`", "",
             f"{len(prs)} pull requests, oldest first, exported with `scripts/github_pr_archive.py` "
             "before the repository moved. Merge commits keep the code; this keeps the discussion.", ""]
    for p in prs:
        n = p["number"]
        state = "merged" if p.get("merged_at") else p["state"]
        lines += [f"## #{n} {p['title']}", "",
                  f"- **{state}** · by {p['user']['login']} · opened {p['created_at'][:10]}"
                  + (f" · merged {p['merged_at'][:10]}" if p.get("merged_at") else "")
                  + (f" · closed {p['closed_at'][:10]}" if p.get("closed_at") and not p.get("merged_at") else ""),
                  f"- `{p['head']['ref']}` → `{p['base']['ref']}`"
                  + (f" · merge commit `{p['merge_commit_sha'][:10]}`" if p.get("merged_at") and p.get("merge_commit_sha") else ""),
                  "", block(p.get("body")), ""]
        reviews = [r for r in gh(f"repos/{slug}/pulls/{n}/reviews") if (r.get("body") or "").strip() or r["state"] != "COMMENTED"]
        code = gh(f"repos/{slug}/pulls/{n}/comments")
        talk = gh(f"repos/{slug}/issues/{n}/comments")
        if reviews or code or talk:
            lines += ["**Discussion**", ""]
        for r in reviews:
            lines += [f"- review by {r['user']['login']} ({r['state'].lower()}, {(r.get('submitted_at') or '')[:10]})", "",
                      block(r.get("body")), ""]
        for c in sorted(code + talk, key=lambda c: c["created_at"]):
            where = f" on `{c['path']}` line {c.get('line') or c.get('original_line')}" if "path" in c else ""
            lines += [f"- {c['user']['login']}{where} ({c['created_at'][:10]})", "", block(c.get("body")), ""]
        print(f"#{n} {state}: {p['title'][:70]}")
    a.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {a.out} ({len(prs)} pull requests)")


if __name__ == "__main__":
    main()
