import fnmatch
import re
from dataclasses import dataclass


@dataclass
class CodeownersEntry:
    pattern: str
    owners: list[str]


def parse_codeowners(content: str) -> list[CodeownersEntry]:
    """Parse a CODEOWNERS file (GitHub's format: `<pattern> <owner> [owner...]`,
    '#' comments, blank lines ignored). Later entries take precedence on a
    match, matching GitHub's own "last match wins" rule."""
    entries = []
    for line in content.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        pattern, owners = parts[0], parts[1:]
        entries.append(CodeownersEntry(pattern=pattern, owners=owners))
    return entries


def _matches(pattern: str, path: str) -> bool:
    # CODEOWNERS patterns are gitignore-style: a leading "/" anchors to the
    # repo root, otherwise the pattern can match starting at any directory
    # depth. A trailing "/" means "everything under this directory".
    rooted = pattern.startswith("/")
    glob = pattern.lstrip("/")
    if glob.endswith("/"):
        glob += "*"

    if fnmatch.fnmatch(path, glob):
        return True
    return not rooted and fnmatch.fnmatch(path, f"*/{glob}")


def owners_for_path(entries: list[CodeownersEntry], path: str) -> list[str]:
    """Which owners apply to a file path, honoring last-match-wins."""
    matched: list[str] = []
    for entry in entries:
        if _matches(entry.pattern, path):
            matched = entry.owners
    return matched


_PATH_LIKE_RE = re.compile(r"\b[\w./-]+\.[a-zA-Z]{1,10}\b|\b[\w-]+/[\w./-]+\b")


def extract_candidate_paths(text: str) -> list[str]:
    """Pull filename/path-looking tokens out of free-form issue text, e.g.
    'crash in worker/jobs.py when...' -> ['worker/jobs.py']."""
    return _PATH_LIKE_RE.findall(text)


def suggest_reviewers(codeowners_content: str, issue_text: str, limit: int = 3) -> list[str]:
    """Heuristic reviewer suggestion: extract path-like tokens from the
    issue text and match them against CODEOWNERS. Recent-commit-author
    fallback (per docs/ARCHITECTURE.md) needs the GitHub API and is added
    when this is wired into agent-core (build order step 5)."""
    entries = parse_codeowners(codeowners_content)
    suggested: list[str] = []
    for path in extract_candidate_paths(issue_text):
        for owner in owners_for_path(entries, path):
            if owner not in suggested:
                suggested.append(owner)
    return suggested[:limit]
