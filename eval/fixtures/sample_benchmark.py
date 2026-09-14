"""A small synthetic benchmark standing in for the real thing: a labeled
set of ~100-200 already-triaged issues from a real repo (docs/ARCHITECTURE.md
section 5). There's no real installation with that history yet, so this
is a handful of made-up issues with both a "ground truth" and a
plausible agent prediction, deliberately including some wrong predictions
so the eval harness's metrics aren't all trivially 100%.
"""

BENCHMARK = [
    {
        "repo_full_name": "acme/widgets",
        "issue_number": 1001,
        "title": "Login button does nothing on Safari",
        "true_labels": ["bug", "needs-triage"],
        "true_duplicate_of": None,
        "predicted_labels": ["bug", "needs-triage"],
        "predicted_duplicate_of": None,
        "action_type": "act",
        "confidence": 0.94,
    },
    {
        "repo_full_name": "acme/widgets",
        "issue_number": 1002,
        "title": "Safari login broken, button unresponsive",
        "true_labels": ["bug"],
        "true_duplicate_of": 1001,
        "predicted_labels": ["bug"],
        "predicted_duplicate_of": 1001,
        "action_type": "act",
        "confidence": 0.91,
    },
    {
        "repo_full_name": "acme/widgets",
        "issue_number": 1003,
        "title": "Add dark mode toggle",
        "true_labels": ["feature"],
        "true_duplicate_of": None,
        "predicted_labels": ["feature", "needs-triage"],
        "predicted_duplicate_of": None,
        "action_type": "escalate",
        "confidence": 0.62,
    },
    {
        "repo_full_name": "acme/widgets",
        "issue_number": 1004,
        "title": "How do I configure webhook retries?",
        "true_labels": ["question"],
        "true_duplicate_of": None,
        "predicted_labels": ["question"],
        "predicted_duplicate_of": None,
        "action_type": "act",
        "confidence": 0.88,
    },
    {
        "repo_full_name": "acme/widgets",
        "issue_number": 1005,
        "title": "Docs missing setup step for pgvector",
        "true_labels": ["docs"],
        "true_duplicate_of": None,
        "predicted_labels": ["bug"],  # wrong: agent misclassified type
        "predicted_duplicate_of": None,
        "action_type": "act",
        "confidence": 0.87,
    },
    {
        "repo_full_name": "acme/widgets",
        "issue_number": 1006,
        "title": "Crash when uploading a file over 10MB",
        "true_labels": ["bug", "high-severity"],
        "true_duplicate_of": None,
        "predicted_labels": ["bug"],  # under-labeled: missed high-severity
        "predicted_duplicate_of": None,
        "action_type": "act",
        "confidence": 0.89,
    },
    {
        "repo_full_name": "acme/widgets",
        "issue_number": 1007,
        "title": "Same crash on large file uploads",
        "true_labels": ["bug", "high-severity"],
        "true_duplicate_of": 1006,
        "predicted_labels": ["bug", "high-severity"],
        "predicted_duplicate_of": None,  # missed: should have linked 1006
        "action_type": "escalate",
        "confidence": 0.7,
    },
    {
        "repo_full_name": "acme/widgets",
        "issue_number": 1008,
        "title": "Feature request: bulk export",
        "true_labels": ["feature"],
        "true_duplicate_of": None,
        "predicted_labels": ["feature"],
        "predicted_duplicate_of": None,
        "action_type": "act",
        "confidence": 0.96,
    },
]
