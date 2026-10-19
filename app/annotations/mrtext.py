"""Markdown descriptions for the MRs/PRs ohmydb opens (drift, proposals).
Long content sits in collapsible <details> blocks, and the text is kept
within gitrepo.DESCRIPTION_MAX by dropping detail step by step (full
lists, then capped lists, then counts only) instead of being cut
mid-markup. Pure functions: service.py builds the data, gitrepo.py ships
the result."""

import html
from collections import defaultdict
from pathlib import PurePosixPath

from app.annotations.gitrepo import DESCRIPTION_MAX, description_size

_CAPS = (None, 50, 10, 0)  # per-database list caps, tried in order; 0 = counts only
_RATIONALE_MAX = 4000
_KEYS_MAX = 30
_FOOTER = "<sub>Opened by ohmydb · the complete change is in the Changes tab</sub>"


def fits(text: str) -> bool:
    return description_size(text) <= DESCRIPTION_MAX


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}{'s' if count != 1 else ''}"


def _details(summary: str, lines: list[str]) -> list[str]:
    # The blank line after <summary> is required, or GitLab/GitHub render
    # the Markdown inside as plain text.
    return [f"<details><summary>{summary}</summary>", "", *lines, "", "</details>", ""]


def _grouped(groups: dict[str, list[str]], cap: int | None) -> list[str]:
    """One <details> per database; cap 0 = a counts table instead."""
    if cap == 0:
        return ["| Database | Count |", "|---|---:|",
                *(f"| `{db}` | {len(lines)} |" for db, lines in sorted(groups.items())), ""]
    out = []
    for db, lines in sorted(groups.items()):
        shown = lines if cap is None else lines[:cap]
        more = [f"- … and {len(lines) - len(shown)} more (see the Changes tab)"] if len(shown) < len(lines) else []
        out += _details(f"<b>{html.escape(db)}</b> — {len(lines)}", [*shown, *more])
    return out


def _clamp(head: list[str], tail: list[str]) -> str:
    """Last resort: keep `tail` whole and as much of `head` as fits."""
    mark = ["", "_… truncated, see the Changes tab_", ""]
    budget = DESCRIPTION_MAX - description_size("\n".join([*mark, *tail])) - 2
    used = 0
    for i, line in enumerate(head):
        used += description_size(line) + 2
        if used > budget:
            return "\n".join([*head[:i], *mark, *tail])
    return "\n".join([*head, *tail])


def drift_description(stubs: list[tuple[str, str, str | None]], removed: list[str],
                      stale: list[tuple[str, list[str]]]) -> str:
    """`stubs`: (db, table, cluster or None) — cluster only in per-cluster
    mode. `removed`: repo-relative paths. `stale`: (path, gone columns)."""
    new = defaultdict(list)
    for db, name, cluster in stubs:
        new[db].append(f"- `{db}.{name}`" + (f" ({cluster})" if cluster else ""))
    gone = defaultdict(list)
    for rel in removed:
        gone[PurePosixPath(rel).parent.name].append(f"- `{rel}`")
    stale_lines = [f"- `{rel}`: " + ", ".join(f"`{c}`" for c in cols) for rel, cols in stale]

    checklist = ["#### ✅ Reviewer checklist", ""]
    if stubs:
        checklist += ["- [ ] Fill in `description` / `grain` where it's worth it (unfilled stubs read as unannotated)",
                      "- [ ] Tables not worth annotating: add them to `ignore` in `_global.yaml`"]
    if removed:
        checklist += ["- [ ] Removed files: restore any table that is coming back (that pauses drift until merged)"]
    tail = [*checklist, "", _FOOTER]  # head always ends with a blank line

    def render(cap: int | None) -> tuple[list[str], list[str]]:
        head = [
            "### 🤖 ohmydb annotation drift", "",
            "The last schema sync found tables without an annotation file and/or annotation files whose "
            "table is gone. ohmydb rebuilds branch `ohmydb/drift` after every sync until this is merged; "
            "pushing your own commits to it pauses that.", "",
            "| | |", "|---|---:|",
            f"| 🆕 New tables (stubs added) | {len(stubs)} |",
            f"| 🗑️ Orphan files (removed) | {len(removed)} |",
            f"| ⚠️ Stale columns (not changed) | {_plural(len(stale), 'file')} |", "",
        ]
        if stubs:
            head += ["#### 🆕 New tables", "", *_grouped(new, cap)]
        if removed:
            head += ["#### 🗑️ Removed files", "",
                     "Their table is no longer in the catalog. To keep one, restore it on this branch.", "",
                     *_grouped(gone, cap)]
        if stale:
            shown = stale_lines if cap is None else stale_lines[:cap]
            more = [f"- … and {len(stale) - len(shown)} more"] if len(shown) < len(stale_lines) else []
            head += ["#### ⚠️ Stale columns", "",
                     "Annotated columns that no longer exist. Not changed by this MR.", "",
                     *_details(_plural(len(stale), "file"), [*shown, *more])]
        return head, tail

    for cap in _CAPS:
        if fits(text := "\n".join(sum(render(cap), []))):
            return text
    return _clamp(*render(0))


def _changed_keys(patch: dict) -> list[tuple[str, bool]]:
    """(dotted key, removed?) to depth 2, e.g. ("columns.ts", False)."""
    out = []
    for key, value in patch.items():
        if isinstance(value, dict) and value:
            out += [(f"{key}.{sub}", v is None) for sub, v in value.items()]
        else:
            out.append((key, value is None))
    return out


def proposal_description(cluster: str, database: str, name: str, rel: str, new_file: bool, patch: dict,
                         rationale: str, via: str) -> str:
    """No diff preview: the MR's Changes tab already shows it. The capped
    rationale and changed-key list keep this far below the budget."""
    if len(rationale) > _RATIONALE_MAX:
        rationale = rationale[:_RATIONALE_MAX] + " …"
    keys = _changed_keys(patch)
    shown = ", ".join(f"`{k}`" + (" (removed)" if gone else "") for k, gone in keys[:_KEYS_MAX])
    if len(keys) > _KEYS_MAX:
        shown += f" and {len(keys) - _KEYS_MAX} more"
    return "\n".join([
        f"### 🤖 ohmydb annotation proposal: `{database}.{name}`", "",
        *(f"> {line}" if line else ">" for line in rationale.splitlines()), "",
        "| | |", "|---|---|",
        f"| 📍 Table | `{database}.{name}` · cluster `{cluster}` |",
        f"| 📄 File | `{rel}` ({'new file' if new_file else 'updated'}) |",
        f"| 🔑 Changed keys | {shown or '—'} |",
        f"| 🛰️ Proposed via | {via} |", "",
        "#### ✅ Reviewer checklist", "",
        "- [ ] The rationale is backed by evidence (a query result, docs, the table owner)",
        "- [ ] Column descriptions and `values` match the data",
        "- [ ] Join keys and the `use_instead` target are right", "",
        _FOOTER,
    ])
