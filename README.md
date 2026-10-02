# Generative AI on Databricks, hands-on labs

Lab guide for a two-day low-code training. Built with MkDocs Material.

```bash
pip install -r requirements.txt
mkdocs serve          # local preview at http://127.0.0.1:8000
mkdocs build          # static site in ./site
python data/generate_synthetic_data.py   # local offline preview only, writes CSVs to data/out
```

Training data itself is set up inside Databricks, not locally, and the repo must stay public so it can
be fetched without credentials. Each participant imports `notebooks/lab_data.py` straight from GitHub
(**Workspace > Import > URL**) and runs it to get their own private schema — no trainer prep beyond a
one-time catalog and permissions setup. The same notebook tears it back down at the end. See
[Trainer notes](docs/trainer-notes.md).

Deployment to GitHub Pages runs automatically from `.github/workflows/deploy.yml` on push to `main`.

Rule for every page: no client names, no client data. Public documents and synthetic data only.

## Slides

Trainer-facing slide decks for the live sessions live in `docs/slides/` (`day1-slides.pptx`,
`day2-slides.pptx`) — the theory content, agenda and recap slides that sit alongside the hands-on labs
in this repo. They're tracked in git but not part of the published site (mkdocs only builds `docs/*.md`);
keep them in sync with the lab guide by hand whenever lab timing or content changes.
