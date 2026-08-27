---
last_reviewed: 2026-08-27
---

# Acro TD Version Manager

Central version and tox management for TouchDesigner components.

## What it does

This module provides three building blocks that the rest of the Acro TD ecosystem (and your own components) build on:

| Class | Role |
|-------|------|
| `AcroToxExt` | Mixin — external tox file management (save/load/reload, save-on-project-save modes) |
| `AcroVersionExt` | Mixin — version tracking on top of `AcroToxExt` (version file, remote update checks, dev-mode bumps) |
| `AcroVersionManager` | Extension — central manager that discovers every `version_tracking` component and runs batch operations |

Any component that inherits from `AcroVersionExt` automatically gets a **Component** page (tox controls), a **Version** page (semver + update controls), the `tox_managed` + `version_tracking` tags, and a version JSON file written next to its tox.

## API surface (at a glance)

```python
# Per-component (any AcroVersionExt-inheriting comp)
comp.SaveTox(prompt=False)               # write tox to disk
comp.ReloadTox()                         # reload tox + refresh version params from JSON
comp.CheckForUpdates()                   # hit Versionurl / git fetch + compare
comp.PromptVersionBump()                 # dev-mode dialog: Major/Minor/Patch/Build/Skip

# Central (op.AVM — the AcroVersionManager extension)
op.AVM.CheckAll()                        # check every version-tracked comp
op.AVM.PrintReport()                     # status report to textport
op.AVM.UpdateAll(updates)                # apply all auto-updatable updates
op.AVM.SkipVersion(comp, version)        # remember a specific skip
op.AVM.IgnoreComponent(comp)             # ignore a component permanently
```

## Where to go next

- **[Tox Management](tox-management)** — `AcroToxExt`: the Component parameter page, save modes (off/prompt/always/auto), tox binding via expressions, tag discovery.
- **[Version Tracking](version-tracking)** — `AcroVersionExt`: the Version parameter page, version file format, remote-source config, dev-mode behavior, override of `ReloadTox()`.
- **[Version Manager](version-manager)** — `AcroVersionManager`: discovery, batch checks, skip/ignore state, lifecycle hooks (`onStart`, `onSaveStart`).
- **[Remote Version Checking](version-checking)** — Versionurl vs. git fetch, token auth for private repos, semantic version comparison.
- **[Dev Workflow](dev-workflow)** — Dev mode, version bump dialog, CHANGELOG generation, auto save-on-bump.

## Installation

Installed as a git subtree in the Acro TD Core template:

```bash
git subtree add --prefix=modules/acro-td-version-manager https://github.com/acronym-lol/acro-td-version-manager.git main --squash
```

Each module's `setup.ps1` / `setup.sh` registers `ACRO_TD_VERSION_MANAGER` pointing at the module on disk so extensions can resolve script paths via `var('ACRO_TD_VERSION_MANAGER')`.
