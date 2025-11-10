# docs/src/generate_api.py
from __future__ import annotations
import importlib
import inspect
import pkgutil
import sys

import mkdocs_gen_files

# --- CONFIG ---
PKG_NAME = "causalinf"   # your top-level package at ./causalinf
SRC_DIR = "."            # add repo root to sys.path so imports work
API_ROOT = "api"         # emit files under docs/api
# ---------------

if SRC_DIR and SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

try:
    root_pkg = importlib.import_module(PKG_NAME)
except Exception as e:
    raise SystemExit(
        f"[generate_api] Could not import '{PKG_NAME}' from '{SRC_DIR}'. {e}"
    )


def write_text(path: str, text: str) -> None:
    """Write a text file relative to the docs/ directory."""
    with mkdocs_gen_files.open(path, "w") as f:
        f.write(text)


def dotted_to_folder(dotted: str) -> str:
    return dotted.replace(".", "/")


def module_index_path(module_name: str) -> str:
    return f"{API_ROOT}/{dotted_to_folder(module_name)}/index.md"


def class_page_path(module_name: str, class_name: str) -> str:
    return f"{API_ROOT}/{dotted_to_folder(module_name)}/classes/{class_name}.md"


def func_page_path(module_name: str, func_name: str) -> str:
    return f"{API_ROOT}/{dotted_to_folder(module_name)}/functions/{func_name}.md"


def is_public(name: str) -> bool:
    return not name.startswith("_")


def safe_import(name: str):
    try:
        return importlib.import_module(name)
    except Exception:
        return None


def iter_modules(pkg):
    """Yield dotted module names under the given package (including the package itself)."""
    yield pkg.__name__
    if hasattr(pkg, "__path__"):
        for m in pkgutil.walk_packages(pkg.__path__, prefix=pkg.__name__ + "."):
            yield m.name


# --- Generate files ---
for mod_name in iter_modules(root_pkg):
    mod = safe_import(mod_name)
    if mod is None:
        # Skip modules that fail to import at doc-build time
        continue

    # Module index page
    mod_idx_path = module_index_path(mod_name)
    write_text(
        mod_idx_path,
        f"""---
title: {mod_name}
---

# `{mod_name}`

::: {mod_name}
    options:
      members: false
      show_root_toc_entry: false
      show_symbol_type_heading: true
      show_source: true

## Members

- **Classes** — see the *classes* folder.
- **Functions** — see the *functions* folder.
"""
    )

    # Per-class pages (only classes defined in this module)
    classes = [
        (name, obj)
        for name, obj in inspect.getmembers(mod, inspect.isclass)
        if obj.__module__ == mod_name and is_public(name)
    ]
    for cls_name, _ in sorted(classes, key=lambda x: x[0].lower()):
        p = class_page_path(mod_name, cls_name)
        write_text(
            p,
            f"""---
title: {mod_name}.{cls_name}
---

# `{mod_name}.{cls_name}`

::: {mod_name}.{cls_name}
    options:
      members: true
      inherited_members: true
      show_source: true
      show_signature: true
      show_symbol_type_heading: true
"""
        )

    # Per-function pages (only functions defined in this module)
    funcs = [
        (name, obj)
        for name, obj in inspect.getmembers(mod, inspect.isfunction)
        if obj.__module__ == mod_name and is_public(name)
    ]
    for fn_name, _ in sorted(funcs, key=lambda x: x[0].lower()):
        p = func_page_path(mod_name, fn_name)
        write_text(
            p,
            f"""---
title: {mod_name}.{fn_name}
---

# `{mod_name}.{fn_name}()`

::: {mod_name}.{fn_name}
    options:
      members: false
      show_source: true
      show_signature: true
      show_symbol_type_heading: true
"""
        )

# API landing page (section index)
api_index = f"{API_ROOT}/index.md"
write_text(
    api_index,
    """---
title: API Reference
---

# API Reference

Browse by module, class, or function using the sidebar.
"""
)
