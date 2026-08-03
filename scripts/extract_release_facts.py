#!/usr/bin/env python3
"""Extract machine-readable release facts from the DocumentDB source tree at a git ref.

The CHANGELOG describes internal release trains and is amended after tags are cut,
so it cannot be trusted as a record of what a release contains. This script derives
the facts directly from the code at a tag:

  - GUCs (name, type, default, min/max, description) from DefineCustom*Variable calls
  - Wire-protocol commands dispatched by the gateway
  - Aggregation pipeline stages (StageDefinitions[])
  - Aggregation expression operators (OperatorExpressions[])
  - Gateway DOCUMENTDB_* environment variables
  - SQL functions/procedures from the *--latest.sql UDF scripts

Usage:
    python extract_release_facts.py --source <path-to-documentdb-repo> --ref v0.114-0 \
        [--out release-facts/v0.114-0.yml]

The source repo is read at the given ref via `git archive`; no checkout is needed and
the working tree of the source repo is never touched.
"""

import argparse
import io
import re
import subprocess
import sys
import tarfile
from pathlib import Path

import yaml

# Directories included in the fact extraction. `internal/` is deliberately excluded:
# it is not part of the shipped OSS packages.
COMPONENTS = {
    "pg_documentdb": "documentdb",
    "pg_documentdb_core": "documentdb_core",
    "pg_documentdb_extended_rum": "documentdb_rum",
    "pg_documentdb_gw": None,  # Rust gateway: no GUCs, has commands/env vars
}

GUC_CALL_RE = re.compile(r"DefineCustom(Bool|Int|Real|String|Enum)Variable\s*\(")
DEFINE_RE = re.compile(r"^[ \t]*#[ \t]*define[ \t]+(\w+)[ \t]+(.+?)[ \t]*$", re.M)


def read_tree(source: str, ref: str) -> dict:
    """Return {path: text} for all files under COMPONENTS at the given ref."""
    cmd = ["git", "-C", source, "archive", "--format=tar", ref, *COMPONENTS]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        sys.exit(f"git archive failed for ref {ref!r}: {proc.stderr.decode(errors='replace')}")
    files = {}
    with tarfile.open(fileobj=io.BytesIO(proc.stdout)) as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            if not member.name.endswith((".c", ".h", ".rs", ".sql")):
                continue
            data = tar.extractfile(member).read()
            files[member.name] = data.decode("utf-8", errors="replace")
    return files


def strip_c_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    return text


def split_call_args(text: str, open_paren: int) -> tuple:
    """Split the argument list of a call whose '(' is at open_paren.

    Returns (args, end_index). Tracks nesting and string/char literals.
    """
    args, depth, current, i = [], 0, [], open_paren
    in_str = in_char = False
    while i < len(text):
        ch = text[i]
        if in_str:
            current.append(ch)
            if ch == "\\":
                current.append(text[i + 1])
                i += 1
            elif ch == '"':
                in_str = False
        elif in_char:
            current.append(ch)
            if ch == "\\":
                current.append(text[i + 1])
                i += 1
            elif ch == "'":
                in_char = False
        elif ch == '"':
            in_str = True
            current.append(ch)
        elif ch == "'":
            in_char = True
            current.append(ch)
        elif ch in "([{":
            depth += 1
            if depth > 1:
                current.append(ch)
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                args.append("".join(current).strip())
                return args, i
            current.append(ch)
        elif ch == "," and depth == 1:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
        i += 1
    raise ValueError("unbalanced parentheses in call")


def join_string_literals(expr: str) -> str:
    """Collapse adjacent C string literals (possibly wrapped in gettext_noop) to one string."""
    expr = re.sub(r"gettext_noop\s*\(", "(", expr)
    parts = re.findall(r'"((?:[^"\\]|\\.)*)"', expr)
    if parts:
        return "".join(parts).replace('\\"', '"').replace("\\n", " ").replace("\\t", " ")
    return expr.strip()


def collect_defines(files: dict) -> dict:
    """Collect simple #define NAME VALUE constants from all C sources."""
    defines = {}
    for path, text in files.items():
        if not path.endswith((".c", ".h")):
            continue
        # Join line continuations before scanning.
        joined = text.replace("\\\n", " ")
        for name, value in DEFINE_RE.findall(joined):
            if name not in defines:
                defines[name] = value.strip()
    return defines


def resolve_constant(expr: str, defines: dict) -> str:
    """Resolve a default-value expression, following #define indirection."""
    seen = set()
    expr = expr.strip()
    while expr in defines and expr not in seen:
        seen.add(expr)
        expr = defines[expr].strip()
    if '"' in expr:
        return join_string_literals(expr)
    return expr


def component_of(path: str) -> str:
    return path.split("/", 1)[0]


def extract_gucs(files: dict) -> list:
    defines = collect_defines(files)
    gucs = []
    for path, raw in sorted(files.items()):
        if not path.endswith((".c", ".h")) or "DefineCustom" not in raw:
            continue
        text = strip_c_comments(raw)
        prefix = COMPONENTS.get(component_of(path))
        for match in GUC_CALL_RE.finditer(text):
            guc_type = match.group(1).lower()
            try:
                args, _ = split_call_args(text, match.end() - 1)
            except ValueError:
                print(f"warning: unparseable DefineCustom call in {path}", file=sys.stderr)
                continue
            if len(args) < 5:
                continue
            name = parse_guc_name(args[0], prefix)
            if name is None:
                print(f"warning: unresolved GUC name {args[0]!r} in {path}", file=sys.stderr)
                continue
            entry = {
                "name": name,
                "type": guc_type,
                "default": resolve_constant(args[4], defines),
                "description": join_string_literals(args[1]),
                "component": component_of(path),
                "file": path,
            }
            if guc_type in ("int", "real") and len(args) >= 7:
                entry["min"] = resolve_constant(args[5], defines)
                entry["max"] = resolve_constant(args[6], defines)
            gucs.append(entry)
    # Deduplicate by name (conditional compilation can register twice); keep first.
    unique = {}
    for guc in gucs:
        unique.setdefault(guc["name"], guc)
    return sorted(unique.values(), key=lambda g: g["name"])


def parse_guc_name(expr: str, prefix: str) -> str | None:
    """Resolve the first DefineCustom argument to a full GUC name."""
    m = re.match(r'psprintf\s*\(\s*"%s\.([^"]+)"', expr)
    if m:
        return f"{prefix}.{m.group(1)}" if prefix else None
    m = re.match(r'"([^"]+)"$', expr.strip())
    if m:
        return m.group(1)
    return None


def find_file(files: dict, suffix: str) -> str | None:
    matches = [p for p in files if p.endswith(suffix)]
    return min(matches, key=len) if matches else None


def extract_commands(files: dict) -> list:
    """Wire commands the gateway actually dispatches (process.rs), with wire names."""
    process = find_file(files, "processor/process.rs")
    types = find_file(files, "requests/request_type.rs")
    if not process or not types:
        print("warning: gateway dispatch files not found at this ref", file=sys.stderr)
        return []
    variants = sorted(set(re.findall(r"RequestType::(\w+)", files[process])))
    wire_names = dict(re.findall(r'Self::(\w+)\s*=>\s*"([^"]+)"', files[types]))
    commands = []
    for variant in variants:
        name = wire_names.get(variant)
        if name:
            commands.append(name)
        else:
            print(f"warning: no wire name for RequestType::{variant}", file=sys.stderr)
    return sorted(set(commands))


def extract_stages(files: dict) -> list:
    path = find_file(files, "aggregation/bson_aggregation_pipeline.c")
    if not path:
        return []
    return sorted(set(re.findall(r'\.stage\s*=\s*"(\$[^"]+)"', files[path])))


def extract_expression_operators(files: dict) -> list:
    path = find_file(files, "operators/bson_expression.c")
    if not path:
        return []
    text = strip_c_comments(files[path])
    m = re.search(r"OperatorExpressions\[\]\s*=\s*\{", text)
    if not m:
        return []
    block, _ = split_call_args(text, m.end() - 1)
    ops = []
    entry_re = re.compile(r'"(\$[\w.]+)"\s*,\s*([&\w]+)\s*,\s*([&\w]+)')
    for entry in block:
        em = entry_re.search(entry)
        if not em:
            continue
        name, parse_fn, handle_fn = em.groups()
        ops.append({
            "name": name,
            "implemented": not (parse_fn == "NULL" and handle_fn == "NULL"),
        })
    unique = {op["name"]: op for op in ops}
    return sorted(unique.values(), key=lambda o: o["name"])


def extract_env_vars(files: dict) -> list:
    names = set()
    for path, text in files.items():
        if not (path.startswith("pg_documentdb_gw") and path.endswith(".rs")):
            continue
        if "test" in path.lower():
            continue
        names.update(re.findall(r'"(DOCUMENTDB_[A-Z0-9_]+)"', text))
    return sorted(n for n in names if not n.startswith("DOCUMENTDB_TEST_"))


def extract_sql_functions(files: dict) -> list:
    func_re = re.compile(
        r"CREATE\s+(?:OR\s+REPLACE\s+)?(FUNCTION|PROCEDURE)\s+([\w]+)\.([\w]+)",
        re.I,
    )
    functions = set()
    for path, text in sorted(files.items()):
        if not path.endswith("--latest.sql"):
            continue
        for kind, schema, name in func_re.findall(text):
            functions.add((schema, name, kind.lower()))
    return [
        {"schema": schema, "name": name, "kind": kind}
        for schema, name, kind in sorted(functions)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="path to the documentdb source repo")
    parser.add_argument("--ref", required=True, help="git ref (tag) to extract facts from")
    parser.add_argument("--out", help="output YAML path (default: release-facts/<ref>.yml)")
    args = parser.parse_args()

    files = read_tree(args.source, args.ref)
    commit = subprocess.run(
        ["git", "-C", args.source, "rev-parse", args.ref],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    facts = {
        "ref": args.ref,
        "commit": commit,
        "gucs": extract_gucs(files),
        "commands": extract_commands(files),
        "aggregation_stages": extract_stages(files),
        "expression_operators": extract_expression_operators(files),
        "gateway_env_vars": extract_env_vars(files),
        "sql_functions": extract_sql_functions(files),
    }

    out = Path(args.out) if args.out else Path("release-facts") / f"{args.ref}.yml"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        yaml.safe_dump(facts, f, sort_keys=False, allow_unicode=True, width=100)

    counts = {k: len(v) for k, v in facts.items() if isinstance(v, list)}
    print(f"{args.ref}: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
