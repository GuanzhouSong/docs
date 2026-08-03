---
title: Release Notes
description: Per-release notes for DocumentDB, derived from the source code at each release tag.
---

# Release Notes

Release notes for each DocumentDB release, derived directly from the source code at the
release's git tag rather than from `CHANGELOG.md` (which tracks internal release trains
and can diverge from tagged releases). The machine-extracted per-release inventories
behind these pages live in the
[`release-facts/`](https://github.com/documentdb/docs/tree/main/release-facts) directory.

## Releases

| Version | Tag date | Notes |
| --- | --- | --- |
| [v0.114-0](v0.114-0.md) | 2026-06-16 | Current release. Schema validation on by default, gateway environment-variable configuration, non-blocking unique index builds. |
| [v0.113-0](v0.113-0.md) | 2026-05-11 | Collation support for non-unique ordered indexes, `$sortGroup` accumulator sort pushdown, TTL dead-entry pruning. |

Older releases are listed on the
[GitHub releases page](https://github.com/documentdb/documentdb/releases).

## Reading documentation for a specific version

- The documentation site always describes the **latest release**; version-sensitive
  facts carry annotations such as *"added in v0.113-0"* or *"default changed in
  v0.114-0"*.
- Frozen per-version snapshots of this documentation are available as git tags on the
  [docs repository](https://github.com/documentdb/docs/tags) — pick the tag matching
  your release to browse the docs exactly as they were.
