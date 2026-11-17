# Publishing a personal GitHub repo

**Do not push this Cursor working copy (or its git history) to a public GitHub repository.**

This branch still contains a prior take-home workbook, HubSpot connector sketches, deliverable memos, and a large account extract under `web/`, `engine/`, `deliverable/`, and `data/`. Those files are **not** the planner. They must not appear in a personal repo **or in git history**.

## Safe publish

From a clean clone of this project, run:

```bash
python3 planner/scripts/pack_github.py /tmp/account-planner
cd /tmp/account-planner
git init
git add .
git commit -m "feat: account assignment and capacity planner"
```

Then create an empty GitHub repository and `git remote add` / `git push` **that** tree. Confirm `git log` has a single commit and a case-insensitive search for employer, CRM token, and take-home strings is empty before you make it public.

The packed tree is: `planner/` (minus leftover workbook paths), `pyproject.toml`, tests, Streamlit config, GitHub Actions, and docs. Demo CSVs are fictional (`Helio Analytics`, `REP-*`).

## After it is public

- Keep `internal/` and `var/` gitignored.
- Do not add HubSpot tokens, company exports, or screenshots of a production CRM.
- Company work happens in a **private** company-managed clone using [COMPANY_BRINGUP.md](COMPANY_BRINGUP.md).
