from mcp_server.github_client import AGENT_COMMENT_MARKER, GitHubClient

from .fakes import FakeGithub, FakeIssue


def test_apply_labels_dry_run_does_not_touch_github():
    github = FakeGithub()
    client = GitHubClient(github, dry_run=True)

    result = client.apply_labels("acme/widgets", 1, ["bug", "needs-triage"])

    assert result.ok is True
    assert result.dry_run is True
    assert "acme/widgets" not in github.repos  # never called get_repo


def test_apply_labels_live_applies_to_issue():
    github = FakeGithub()
    client = GitHubClient(github, dry_run=False)

    client.apply_labels("acme/widgets", 1, ["bug"])

    issue = github.get_repo("acme/widgets").get_issue(1)
    assert issue.labels_applied == ["bug"]


def test_post_comment_live_marks_body():
    github = FakeGithub()
    client = GitHubClient(github, dry_run=False)

    client.post_comment("acme/widgets", 1, "Thanks for filing this!")

    issue = github.get_repo("acme/widgets").get_issue(1)
    assert len(issue.comments) == 1
    assert AGENT_COMMENT_MARKER in issue.comments[0].body
    assert "Thanks for filing this!" in issue.comments[0].body


def test_post_comment_is_no_spam_idempotent():
    github = FakeGithub()
    client = GitHubClient(github, dry_run=False)

    first = client.post_comment("acme/widgets", 1, "first pass")
    second = client.post_comment("acme/widgets", 1, "second pass, should be skipped")

    issue = github.get_repo("acme/widgets").get_issue(1)
    assert first.skipped_reason is None
    assert second.skipped_reason == "already_commented"
    assert len(issue.comments) == 1


def test_assign_reviewer_live():
    github = FakeGithub()
    client = GitHubClient(github, dry_run=False)

    client.assign_reviewer("acme/widgets", 1, "octocat")

    issue = github.get_repo("acme/widgets").get_issue(1)
    assert issue.assignees == ["octocat"]


def test_link_duplicate_comments_with_reference():
    github = FakeGithub()
    client = GitHubClient(github, dry_run=False)

    client.link_duplicate("acme/widgets", 5, duplicate_of=2)

    issue = github.get_repo("acme/widgets").get_issue(5)
    assert "#2" in issue.comments[0].body


def test_search_issues_maps_results():
    github = FakeGithub()
    github.search_results = [FakeIssue(1, "bug a", "open"), FakeIssue(2, "bug b", "closed")]
    client = GitHubClient(github, dry_run=False)

    results = client.search_issues("acme/widgets", "is:issue bug", limit=10)

    assert results == [
        {"number": 1, "title": "bug a", "state": "open"},
        {"number": 2, "title": "bug b", "state": "closed"},
    ]


def test_search_issues_respects_limit():
    github = FakeGithub()
    github.search_results = [FakeIssue(i) for i in range(5)]
    client = GitHubClient(github, dry_run=False)

    results = client.search_issues("acme/widgets", "bug", limit=2)

    assert len(results) == 2
