# Project: causalinf

## Structure
- `causalinf/` --- Python source code for the package
- `docs/` --- MkDocs web documentation
- `mkdocs.yml` --- MkDocs configuration
- `pyproject.toml` --- Project toml

## Org-mode workflow
- Documentation is written in org-mode (.org) files within `docs/`
- The .md files in docs/ are EXPORTED from org-mode - never edit them directly
- To update documentation content, edit the .org source, then re-export to .md
- Only mkdocs.yml and non-content .md files (e.g. index stubs) may be edited directly
- Use the file `/docs/usage/summary-and-reporting.org` as a template for how the .org files should be structured

## Commands
- `mkdocs serve` - live preview at localhost:8000
- `mkdocs build` - build static site to site/
- `pip install -e .` - install package in dev mode
- `pytest` - run tests
- `~/Dropbox/CienciasSociais/studies/computing/linux/ubuntu/emacs-org2md.sh <file.org>` — export an org file to .md using org2md


## General rules
- Ask which file to edit before modifying anything in docs/
- Prefer explicit over clever
- When unsure about intent, ask before implementing
