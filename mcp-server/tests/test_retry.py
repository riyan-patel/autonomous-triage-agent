import pytest
from github import GithubException

from mcp_server.github_client import MAX_ATTEMPTS, GitHubClient


def make_client(sleeps: list) -> GitHubClient:
    return GitHubClient(github=None, dry_run=False, sleep=sleeps.append)


def test_call_retries_on_429_then_succeeds():
    attempts = []

    def flaky():
        attempts.append(1)
        if len(attempts) < 2:
            raise GithubException(429, {}, {"retry-after": "0"})
        return "ok"

    sleeps = []
    result = make_client(sleeps)._call(flaky)

    assert result == "ok"
    assert len(attempts) == 2
    assert sleeps == [0.0]


def test_call_honors_retry_after_header():
    def always_429():
        raise GithubException(429, {}, {"retry-after": "5"})

    sleeps = []
    with pytest.raises(GithubException):
        make_client(sleeps)._call(always_429)

    assert sleeps == [5.0, 5.0]  # MAX_ATTEMPTS=3 -> 2 retries before giving up


def test_call_falls_back_to_exponential_backoff_without_header():
    def always_403():
        raise GithubException(403, {}, {})

    sleeps = []
    with pytest.raises(GithubException):
        make_client(sleeps)._call(always_403)

    assert sleeps == [1.0, 2.0]


def test_call_gives_up_after_max_attempts():
    attempts = []

    def always_fails():
        attempts.append(1)
        raise GithubException(429, {}, {})

    with pytest.raises(GithubException):
        make_client([])._call(always_fails)

    assert len(attempts) == MAX_ATTEMPTS


def test_call_does_not_retry_non_retryable_status():
    attempts = []

    def fails_404():
        attempts.append(1)
        raise GithubException(404, {}, {})

    sleeps = []
    with pytest.raises(GithubException):
        make_client(sleeps)._call(fails_404)

    assert len(attempts) == 1
    assert sleeps == []
