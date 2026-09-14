"""Minimal fakes standing in for PyGithub's object graph so tests never hit
the real GitHub API. Each fake exposes only the surface GitHubClient uses.
"""


class FakeComment:
    def __init__(self, body: str) -> None:
        self.body = body


class FakeIssue:
    def __init__(self, number: int, title: str = "", state: str = "open") -> None:
        self.number = number
        self.title = title
        self.state = state
        self.labels_applied: list[str] = []
        self.assignees: list[str] = []
        self.comments: list[FakeComment] = []

    def add_to_labels(self, *labels: str) -> None:
        self.labels_applied.extend(labels)

    def add_to_assignees(self, username: str) -> None:
        self.assignees.append(username)

    def create_comment(self, body: str) -> None:
        self.comments.append(FakeComment(body))

    def get_comments(self) -> list[FakeComment]:
        return self.comments


class FakeRepo:
    def __init__(self) -> None:
        self.issues: dict[int, FakeIssue] = {}

    def get_issue(self, number: int) -> FakeIssue:
        return self.issues.setdefault(number, FakeIssue(number))


class FakeGithub:
    def __init__(self) -> None:
        self.repos: dict[str, FakeRepo] = {}
        self.search_results: list[FakeIssue] = []

    def get_repo(self, full_name: str) -> FakeRepo:
        return self.repos.setdefault(full_name, FakeRepo())

    def search_issues(self, query: str) -> list[FakeIssue]:
        return self.search_results
