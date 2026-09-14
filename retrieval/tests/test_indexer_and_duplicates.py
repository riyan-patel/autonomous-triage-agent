import uuid

from retrieval.duplicates import find_similar_issues
from retrieval.indexer import index_issue

from .fakes import FakeEmbedder


def unique_repo() -> str:
    # Each test gets its own fake repo namespace so cosine search results
    # are never polluted by rows another test happened to leave behind.
    return f"acme/test-{uuid.uuid4().hex[:8]}"


def test_index_issue_creates_row(db_session):
    embedder = FakeEmbedder()
    repo = unique_repo()

    issue = index_issue(
        db_session,
        embedder,
        repo_full_name=repo,
        issue_number=1,
        title="Login button does nothing",
        body="Clicking login on Safari does not trigger the auth flow.",
    )

    assert issue.id is not None
    assert issue.embedding is not None
    assert len(issue.embedding) == embedder.dimension


def test_index_issue_upserts_on_repeat(db_session):
    embedder = FakeEmbedder()
    repo = unique_repo()

    first = index_issue(db_session, embedder, repo_full_name=repo, issue_number=1, title="v1", body="")
    second = index_issue(db_session, embedder, repo_full_name=repo, issue_number=1, title="v2 edited", body="")

    assert first.id == second.id
    assert second.title == "v2 edited"


def test_find_similar_issues_ranks_near_duplicate_first(db_session):
    embedder = FakeEmbedder()
    repo = unique_repo()

    index_issue(
        db_session, embedder, repo_full_name=repo, issue_number=1,
        title="Login button broken on Safari",
        body="Clicking login on Safari does nothing, auth flow never starts.",
    )
    index_issue(
        db_session, embedder, repo_full_name=repo, issue_number=2,
        title="Login broken in Safari browser",
        body="The login button does not trigger auth when using Safari.",
    )
    index_issue(
        db_session, embedder, repo_full_name=repo, issue_number=3,
        title="Add dark mode support",
        body="Please add a dark theme toggle to the settings page.",
    )

    query_embedding = embedder.embed("Login button broken on Safari\n\nClicking login on Safari does nothing, auth flow never starts.")
    results = find_similar_issues(
        db_session, repo_full_name=repo, embedding=query_embedding, exclude_issue_number=1, limit=5
    )

    assert results[0].issue_number == 2
    assert results[0].distance < results[-1].distance


def test_find_similar_issues_scoped_to_repo(db_session):
    embedder = FakeEmbedder()
    repo_a = unique_repo()
    repo_b = unique_repo()

    index_issue(db_session, embedder, repo_full_name=repo_a, issue_number=1, title="crash on startup", body="")
    index_issue(db_session, embedder, repo_full_name=repo_b, issue_number=1, title="crash on startup", body="")

    query_embedding = embedder.embed("crash on startup")
    results = find_similar_issues(db_session, repo_full_name=repo_a, embedding=query_embedding, limit=5)

    assert len(results) == 1
