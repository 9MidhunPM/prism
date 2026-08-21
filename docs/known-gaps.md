# Known gaps and release notes

This page keeps the documentation honest about the difference between the
product contract and the latest fetched implementation.

## Luna-only runtime is not yet enforced everywhere

The project contract requires `gpt-5.6-luna` for every runtime AI operation.
The latest source baseline still contains legacy model settings and dispatch in
`backend/app/ai.py`:

- perception and grading resolve `settings.luna_model`;
- review and exam import resolve `settings.gpt4o_model`;
- teacher chat and analysis paths can resolve `settings.gpt4o_mini_model`.

This is a release-blocking implementation gap. The documentation describes the
desired contract, but the running application must not be advertised as
Luna-only until the dispatch function and configuration are corrected and
covered by a test that asserts every operation's selected model.

## UI screenshots need a live capture pass

The current documentation includes two neutral SVG wireframes because a
browser automation surface was unavailable during this pass. They are not
runtime evidence. Before a public demo or submission, capture the teacher
dashboard, rubric, paper review, override history, profile, analytics, and
assistant from a seeded local/staging environment and label each image with its
source commit.

## Documentation freshness

The refresh is based on commit `e2806612fbb05d7d2d50057070d32a9e5bfeae93`.
After implementation changes, recheck:

1. route names and API endpoints;
2. AI operation versions and selected models;
3. processing states and retry behavior;
4. deletion and media retention semantics;
5. screenshot captions and seeded data.
