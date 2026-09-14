from retrieval.reviewer_routing import (
    extract_candidate_paths,
    owners_for_path,
    parse_codeowners,
    suggest_reviewers,
)

CODEOWNERS = """
# default owner
*                   @acme/maintainers

/worker/            @acme/backend-team
/dashboard/         @acme/frontend-team
*.sql               @acme/data-team
"""


def test_parse_codeowners():
    entries = parse_codeowners(CODEOWNERS)
    assert entries[0].pattern == "*"
    assert entries[0].owners == ["@acme/maintainers"]
    assert entries[1].pattern == "/worker/"
    assert entries[1].owners == ["@acme/backend-team"]


def test_owners_for_path_last_match_wins():
    entries = parse_codeowners(CODEOWNERS)
    # /worker/jobs.py matches both "*" (default) and "/worker/" - last wins.
    assert owners_for_path(entries, "worker/jobs.py") == ["@acme/backend-team"]


def test_owners_for_path_falls_back_to_default():
    entries = parse_codeowners(CODEOWNERS)
    assert owners_for_path(entries, "docs/README.md") == ["@acme/maintainers"]


def test_extract_candidate_paths():
    text = "Crash happens in worker/jobs.py when processing db/migrations/0001_init.sql"
    paths = extract_candidate_paths(text)
    assert "worker/jobs.py" in paths
    assert any("migrations" in p for p in paths)


def test_suggest_reviewers_end_to_end():
    issue_text = "Getting an error in worker/jobs.py after the queue retries."
    suggested = suggest_reviewers(CODEOWNERS, issue_text)
    assert suggested == ["@acme/backend-team"]


def test_suggest_reviewers_respects_limit():
    issue_text = "worker/jobs.py and dashboard/App.tsx and schema.sql all involved"
    suggested = suggest_reviewers(CODEOWNERS, issue_text, limit=2)
    assert len(suggested) <= 2
