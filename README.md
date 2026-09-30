# Acro TD Version Manager

[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://acronym-lol.github.io/acro-td-version-manager/)

Central version and tox management for TouchDesigner components.

**Documentation:** https://acronym-lol.github.io/acro-td-version-manager/

## Features

- Discovers all version-tracked components via `version_tracking` tag
- Batch version checking across all components
- Automatic update handling with configurable modes
- Startup version check with configurable delay
- Print reports and popup notifications

## Usage

```python
# Check all components for updates
op.VersionManager.CheckAll()

# Print version report to textport
op.VersionManager.PrintReport()

# Get all tracked components
op.VersionManager.TrackedComponents
```

## Installation

This module is typically installed as a git subtree in the acro-td-core template.

```bash
git subtree add --prefix=modules/acro-td-version-manager https://github.com/acronym-lol/acro-td-version-manager.git main --squash
```
