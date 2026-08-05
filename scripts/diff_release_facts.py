#!/usr/bin/env python3
"""Diff two release-facts files and print the true release delta as Markdown.

Usage:
    python diff_release_facts.py release-facts/v0.113-0.yml release-facts/v0.114-0.yml \
        [--out release-facts/deltas/v0.114-0.md]

This is the changelog-independent record of what actually changed between two tags:
GUCs added/removed and defaults that flipped, commands/stages/operators that appeared
or disappeared, gateway environment variables, and SQL function surface changes.
"""

import argparse
import sys
from pathlib import Path

import yaml


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def keyed(items: list, key) -> dict:
    return {key(item): item for item in items}


def simple_diff(old: list, new: list) -> tuple:
    old_set, new_set = set(old), set(new)
    return sorted(new_set - old_set), sorted(old_set - new_set)


def section(lines: list, title: str, rows: list) -> None:
    if not rows:
        return
    lines.append(f"### {title}")
    lines.append("")
    lines.extend(rows)
    lines.append("")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old", help="facts file for the earlier tag")
    parser.add_argument("new", help="facts file for the later tag")
    parser.add_argument("--out", help="write Markdown here instead of stdout")
    args = parser.parse_args()

    old, new = load(args.old), load(args.new)
    lines = [
        f"# Release delta: {old['ref']} → {new['ref']}",
        "",
        f"Derived from source code at tags `{old['ref']}` ({old['commit'][:10]}) and"
        f" `{new['ref']}` ({new['commit'][:10]}). Independent of CHANGELOG.md.",
        "",
    ]

    # --- GUCs ---
    old_gucs = keyed(old["gucs"], lambda g: g["name"])
    new_gucs = keyed(new["gucs"], lambda g: g["name"])
    added = sorted(set(new_gucs) - set(old_gucs))
    removed = sorted(set(old_gucs) - set(new_gucs))
    changed = sorted(
        name
        for name in set(old_gucs) & set(new_gucs)
        if old_gucs[name]["default"] != new_gucs[name]["default"]
    )

    lines.append("## Configuration (GUCs)")
    lines.append("")
    section(
        lines,
        f"Default changes ({len(changed)})",
        [
            f"- `{name}`: `{old_gucs[name]['default']}` → `{new_gucs[name]['default']}`"
            for name in changed
        ],
    )
    section(
        lines,
        f"Added ({len(added)})",
        [
            f"- `{name}` ({new_gucs[name]['type']}, default `{new_gucs[name]['default']}`)"
            f" — {new_gucs[name]['description']}"
            for name in added
        ],
    )
    section(
        lines,
        f"Removed ({len(removed)})",
        [f"- `{name}`" for name in removed],
    )
    if not (added or removed or changed):
        lines.append("No changes.")
        lines.append("")

    # --- simple string surfaces ---
    for title, field, fmt in [
        ("Wire commands", "commands", "`{}`"),
        ("Aggregation stages", "aggregation_stages", "`{}`"),
        ("Gateway environment variables", "gateway_env_vars", "`{}`"),
    ]:
        added, removed = simple_diff(old[field], new[field])
        if added or removed:
            lines.append(f"## {title}")
            lines.append("")
            section(lines, f"Added ({len(added)})", [f"- {fmt.format(x)}" for x in added])
            section(lines, f"Removed ({len(removed)})", [f"- {fmt.format(x)}" for x in removed])

    # --- expression operators (implemented flag matters) ---
    old_ops = keyed(old["expression_operators"], lambda o: o["name"])
    new_ops = keyed(new["expression_operators"], lambda o: o["name"])
    added = sorted(set(new_ops) - set(old_ops))
    removed = sorted(set(old_ops) - set(new_ops))
    impl_changed = sorted(
        name
        for name in set(old_ops) & set(new_ops)
        if old_ops[name]["implemented"] != new_ops[name]["implemented"]
    )
    if added or removed or impl_changed:
        lines.append("## Expression operators")
        lines.append("")
        section(
            lines,
            f"Added ({len(added)})",
            [
                f"- `{name}`" + ("" if new_ops[name]["implemented"] else " (registered, not implemented)")
                for name in added
            ],
        )
        section(
            lines,
            f"Implementation status changed ({len(impl_changed)})",
            [
                f"- `{name}`: implemented `{old_ops[name]['implemented']}` → `{new_ops[name]['implemented']}`"
                for name in impl_changed
            ],
        )
        section(lines, f"Removed ({len(removed)})", [f"- `{name}`" for name in removed])

    # --- SQL functions ---
    old_fns = {(f["schema"], f["name"]) for f in old["sql_functions"]}
    new_fns = {(f["schema"], f["name"]) for f in new["sql_functions"]}
    added = sorted(new_fns - old_fns)
    removed = sorted(old_fns - new_fns)
    if added or removed:
        lines.append("## SQL functions (from *--latest.sql UDF scripts)")
        lines.append("")
        section(
            lines,
            f"Added ({len(added)})",
            [f"- `{schema}.{name}`" for schema, name in added],
        )
        section(
            lines,
            f"Removed ({len(removed)})",
            [f"- `{schema}.{name}`" for schema, name in removed],
        )

    text = "\n".join(lines).rstrip() + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
