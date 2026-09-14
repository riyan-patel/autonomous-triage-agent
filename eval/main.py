"""CLI entrypoint: python -m eval.main (run from the repo root so the
sibling `retrieval` package resolves)."""

from retrieval.db import get_engine, get_session_factory

from .report import format_report, run_report


def main() -> None:
    engine = get_engine()
    session = get_session_factory(engine)()
    try:
        report = run_report(session)
    finally:
        session.close()

    print(format_report(report))


if __name__ == "__main__":
    main()
