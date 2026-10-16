import json

from issuepilot.github import BOT_LOGIN, Completed, GitHub
from issuepilot.render import MARKER


class FakeGh:
    """Records gh calls and answers them from a small in-memory GitHub."""

    def __init__(self, comments=None, missing=()):
        self.comments = comments or []
        self.missing = set(missing)
        self.calls = []

    def __call__(self, args, stdin=None):
        self.calls.append((args, stdin))
        path = args[1]
        if "--jq" in args:  # listing comments, filtered like the real jq query
            ids = [str(c["id"]) for c in self.comments if c["user"] == BOT_LOGIN and c["body"].startswith(MARKER)]
            return Completed(0, "\n".join(ids), "")
        if path.split("/", 3)[-1] in self.missing:
            return Completed(1, "", "gh: Not Found (HTTP 404)")
        return Completed(0, "", "")


def method(call):
    args = call[0]
    return args[args.index("--method") + 1] if "--method" in args else "GET"


def test_creates_a_comment_when_none_exists():
    gh = FakeGh(comments=[{"id": 5, "user": "berke", "body": "Thanks"}])
    assert GitHub("o/r", gh).upsert_comment(2, "new body") == "created"
    post = gh.calls[-1]
    assert method(post) == "POST" and post[0][1] == "repos/o/r/issues/2/comments"
    assert json.loads(post[1]) == {"body": "new body"}


def test_updates_its_own_latest_comment_instead_of_adding_one():
    gh = FakeGh(comments=[
        {"id": 7, "user": BOT_LOGIN, "body": MARKER + "\nold"},
        {"id": 9, "user": BOT_LOGIN, "body": MARKER + "\nolder retry"},
    ])
    assert GitHub("o/r", gh).upsert_comment(2, "fresh") == "updated"
    patch = gh.calls[-1]
    assert method(patch) == "PATCH" and patch[0][1] == "repos/o/r/issues/comments/9"


def test_a_marker_posted_by_someone_else_is_not_taken_over():
    gh = FakeGh(comments=[{"id": 3, "user": "mallory", "body": MARKER + "\nfake"}])
    assert GitHub("o/r", gh).upsert_comment(2, "x") == "created"


def test_reference_checks():
    gh = FakeGh(missing={"issues/99", "commits/deadbee"})
    github = GitHub("o/r", gh)
    assert github.ref_exists("issue", "#1") is True
    assert github.ref_exists("pull_request", "12") is True
    assert github.ref_exists("issue", "#99") is False
    assert github.ref_exists("commit", "e4a5f61") is True
    assert github.ref_exists("commit", "deadbee") is False
    assert github.ref_exists("commit", "HEAD~1") is False  # not a SHA: never sent to the API
    assert github.ref_exists("issue", "see above") is False


def test_unclear_api_errors_do_not_drop_a_reference():
    def flaky(args, stdin=None):
        return Completed(1, "", "gh: Server Error (HTTP 502)")

    assert GitHub("o/r", flaky).ref_exists("issue", "#1") is None
