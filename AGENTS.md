# Instructions for AI coding assistants

Read `PROJECT_CONTEXT.md` first. It describes the course, the team, the product, the stack
(Python + Flask + SQL Server LocalDB), where every number comes from (`tools/pm_calculations.py`),
how documents are built (`tools/build_docx.py`), the Git branching rules, and what is still to do.

Short rules:
- Documents are written in simple English. Edit Markdown in `docs/`, then run `python tools/build_docx.py`.
- Never change a PM number only in a document; change `tools/pm_calculations.py` and re-run it.
- Run `python -m unittest discover -s tests -v` from `app/` before committing.
- Work on a `feature/*` branch and merge into `develop` with a pull request.
