---
last_reviewed: 2026-08-27
---

# AcroVersionExt — Version Tracking Extension

## Overview

`AcroVersionExt` provides automatic version tracking, remote update checking, and developer workflow tooling for TouchDesigner components. It inherits from `AcroToxExt`, meaning every version-tracked component is also a tox-managed component. This dual inheritance ensures that version-tracked components carry both the `tox_managed` and `version_tracking` tags, enabling discovery through either tag.

```
AcroToxExt
  └── AcroVersionExt
```

The extension manages a local JSON version file on disk, exposes version metadata as read-only parameters, supports remote version checking over HTTP or Git, and provides a developer-facing workflow for version bumping and changelog generation.

---

## Version Parameter Page

`AcroVersionExt` creates a custom parameter page named **Version** on the host component. Parameters are defined as tuples in the format:

```python
(name, label, default, read_only, param_type, help_text, order, enable_expr)
```

| Name | Label | Type | Default | Read Only | Description | Enable Condition |
|------|-------|------|---------|-----------|-------------|------------------|
| `Versionfile` | Version File | `file` | `{project.folder}/{comp.name.lower()}-version.json` | No | Path to the local version JSON file. | Always enabled |
| — | **Version Info** (header) | — | — | — | Section separator for version metadata. | — |
| `Version` | Version | `str` | `1.0.0` | Yes | Semantic version string (Major.Minor.Patch). | Always enabled |
| `Build` | Build | `str` | `0` | Yes | Incremental build number. | Always enabled |
| `Tdversion` | TD Version | `str` | *(empty)* | Yes | TouchDesigner version used for the last build. | Always enabled |
| `Tdbuild` | TD Build | `str` | *(empty)* | Yes | TouchDesigner build number used for the last build. | Always enabled |
| `Lastupdate` | Last Update | `str` | *(empty)* | Yes | ISO 8601 timestamp of the last version update. | Always enabled |
| — | **Remote Source** (header) | — | — | — | Section separator for remote source configuration. | — |
| `Versionurl` | Version URL | `str` | *(empty)* | No | HTTP URL to a remote version JSON file for update checks. | Always enabled |
| `Usetoken` | Use Token | `toggle` | `False` | No | Enable token-based authentication for remote version requests. | Always enabled |
| `Token` | Token | `str` | *(empty)* | No | Authentication token sent with remote version requests. | `me.par.Usetoken` |
| — | **Updates** (header) | — | — | — | Section separator for update behavior. | — |
| `Versioncheckenabled` | Version Check Enabled | `toggle` | `True` | No | Master toggle for remote version checking. | Always enabled |
| `Autoupdate` | Auto Update | `menu` | `off` | No | Update behavior: `off` (Disabled), `prompt` (Prompt to Update), `always` (Always Update). | `me.par.Versioncheckenabled` |
| `Reloadonupdate` | Reload on Update | `toggle` | `True` | No | Reload the tox from disk after a successful update. | `me.par.Autoupdate != 'off'` |
| — | **Development** (header) | — | — | — | Section separator for development settings. | — |
| `Devmode` | Dev Mode | `menu` | `off` | No | Developer mode: `off` (Disabled), `auto` (Auto — In Repo), `always` (Always). | Always enabled |
| `Onlybumpdirty` | Only Bump When Dirty | `toggle` | `True` | No | Skip the version-bump prompt unless the component is dirty. When off, every save asks to bump (useful for project-level scene tracking). | Always enabled |
| `Forcebump` | Force Version Bump | `pulse` | — | No | Manually trigger the version bump dialog. Bypasses both the dev-mode gate and the dirty check. | Always enabled |

---

## Version File Format

The version file is a JSON document stored on disk at the path specified by the `Versionfile` parameter. If the file does not exist when the extension initializes, `_ensureVersionFile()` creates it automatically with default values.

### Schema

| Field | Type | Description |
|-------|------|-------------|
| `version` | `string` | Semantic version in `Major.Minor.Patch` format. |
| `build` | `integer` | Incremental build number. |
| `last_update` | `string` | ISO 8601 timestamp of the last update. |
| `td_version` | `string` | TouchDesigner application version identifier. |
| `td_build` | `string` | TouchDesigner build number string. |

### Example

```json
{
  "version": "1.6.1",
  "build": 294,
  "last_update": "2026-02-19T12:53:32.732217",
  "td_version": "099",
  "td_build": "2025.32280"
}
```

---

## Properties Reference

| Property | Return Type | Description |
|----------|-------------|-------------|
| `Versionfile` | `str` | Resolved path to the version JSON file. |
| `VersionInfo` | `dict` | Parsed contents of the version file as a dictionary. |
| `VersionString` | `str` | Formatted version string, e.g. `'v1.0.0.123'` (version + build). |
| `VersionUrl` | `str` | The configured remote version URL. |
| `VersionCheckEnabled` | `bool` | Whether remote version checking is enabled. |
| `Devmode` | `str` | Current dev mode value (`'off'`, `'auto'`, or `'always'`). |
| `Token` | `str` | The configured authentication token. |
| `Usetoken` | `bool` | Whether token authentication is enabled. |
| `Autoupdate` | `str` | Current auto-update mode (`'off'`, `'prompt'`, or `'always'`). |
| `Reloadonupdate` | `bool` | Whether the tox reloads automatically after an update. |
| `Onlybumpdirty` | `bool` | Whether `PromptVersionBump` skips when the component isn't dirty. |

---

## Methods Reference

| Method | Arguments | Returns | Description |
|--------|-----------|---------|-------------|
| `ReloadTox()` | None | None | Overrides `AcroToxExt.ReloadTox()`. Calls `super().ReloadTox()` and then `_refreshVersionFromDisk()` to ensure version parameters reflect the newly loaded tox. |
| `GetRemoteVersion()` | None | `dict` | Fetches the remote version info. Tries the HTTP URL first (with optional token authentication via the `Token` parameter). Falls back to git fetch, checking `origin/HEAD`, `origin/main`, and `origin/master` in order. |
| `CompareVersions(local, remote)` | `local: dict`, `remote: dict` | `int` | Compares two version info dictionaries. Returns `1` if local is ahead, `-1` if remote is ahead, or `0` if they are equal. |
| `HasUpdate()` | None | `tuple[bool, dict]` | Returns a tuple of `(has_update, remote_info)`. Skips the check and returns `(False, ...)` if dev mode is active or version checking is disabled. |
| `CheckForUpdates()` | None | None | Runs `HasUpdate()` and logs the results. Detects when the local version is ahead of remote and produces devmode-aware log messages. |
| `UpdateVersionParams(version=None, build=None, td_version=None, td_build=None, last_update=None)` | See signature | None | Temporarily unlocks read-only parameters to write version data. Parameters already holding the given value are left untouched, so a no-op refresh does not dirty the component. `Lastupdate` is set to `last_update` when given, otherwise stamped with the current time only if a version field actually changed. |
| `PerformUpdate(remote_version)` | `remote_version: dict` | None | Applies a remote update. Respects the `Autoupdate` mode — prompts or auto-applies depending on configuration. Performs `git pull`, reloads the tox (if enabled), and updates version parameters. |
| `PromptVersionBump(force=False)` | `force: bool` | None | Active when dev mode is engaged (or `force=True`). When the component is dirty (or `Onlybumpdirty` is off), prompts the user to choose Major / Minor / Patch / Build / Don't Save. Build saves with only a build-number bump; Major/Minor/Patch additionally append a CHANGELOG entry and update the version file. On any save, the tox is auto-saved to capture the bump. `force=True` bypasses both the dev-mode gate and the dirty check — wired to the `Forcebump` pulse. |
| `UpdateVersionFile(new_version, new_build)` | `new_version: str`, `new_build: int` | None | Writes a new version file to disk with the provided version string, build number, current timestamp, and current TouchDesigner version info. |
| `UpdateChangelog(new_version)` | `new_version: str` | None | Creates or updates a `CHANGELOG.md` file with an entry for the new version, then opens it in the system editor. |
| `GetBuildNumberFromProjectName()` | None | `int` | Extracts the build number from the project file name. Expects the format `Name.123.toe` and returns the integer `123`. |

### Internal Methods

| Method | Arguments | Returns | Description |
|--------|-----------|---------|-------------|
| `_isDevActive()` | None | `bool` | Resolves the current dev mode setting: `off` returns `False`, `auto` returns `True` if the component is inside a git repository (`IsInRepo`), `always` returns `True`. |
| `_ensureVersionFile()` | None | None | Called during initialization. If the version file does not exist at the configured path, creates it with default values. |
| `_refreshVersionFromDisk()` | None | None | Reads the version file from disk and updates all read-only version parameters to reflect the current file contents. |

---

## How ReloadTox Override Works

`AcroVersionExt` overrides the `ReloadTox()` method inherited from `AcroToxExt`. The override follows a two-step sequence:

1. Calls `super().ReloadTox()` to execute the standard tox reload logic from `AcroToxExt` (which handles the actual `.tox` file reload from disk).
2. Calls `_refreshVersionFromDisk()` to re-read the version JSON file and update all version-related parameters on the component.

This ensures that after any tox reload — whether triggered manually, by an update, or by the tox management system — the displayed version parameters always reflect the version file that shipped with the reloaded tox.

```python
def ReloadTox(self):
    super().ReloadTox()
    self._refreshVersionFromDisk()
```

---

## Dev Mode

The `Devmode` parameter controls developer-specific behaviors such as version bump prompting and update suppression. The internal method `_isDevActive()` resolves the parameter value into a boolean:

| Devmode Value | Label | `_isDevActive()` Result | Behavior |
|---------------|-------|-------------------------|----------|
| `off` | Disabled | `False` | No developer features. Updates are checked and applied normally. |
| `auto` | Auto (In Repo) | Result of `IsInRepo` | Developer features activate only when the component resides inside a git repository. This is the recommended setting for components under active development. |
| `always` | Always | `True` | Developer features are always active regardless of repository status. |

When dev mode is active:

- `HasUpdate()` skips the remote check and returns no update available, preventing accidental overwrites of local development changes.
- `CheckForUpdates()` produces devmode-aware log messages when the local version is ahead of remote.
- `PromptVersionBump()` becomes operational. The bump dialog offers Major / Minor / Patch / Build / Don't Save:
  - **Major / Minor / Patch** — bump the semantic version, append a CHANGELOG entry, update the version file, and save the tox.
  - **Build** — save with a fresh build number only (no semantic bump, no CHANGELOG entry).
  - **Don't Save** — skip everything; the component remains dirty.
- The `Onlybumpdirty` toggle gates the dirty check — when off, the prompt fires on every save regardless of dirty state, useful for scene-level tracking.
- The `Forcebump` pulse calls `PromptVersionBump(force=True)`, which bypasses both the dev-mode gate and the dirty check.

```python
def _isDevActive(self):
    mode = self.Devmode
    if mode == 'off':
        return False
    elif mode == 'auto':
        return self.IsInRepo
    elif mode == 'always':
        return True
```

---

## Usage Example

The following example demonstrates how to create a custom extension class that inherits from `AcroVersionExt`, thereby gaining both tox management and version tracking capabilities.

```python
from tdversionext import AcroVersionExt

class MyComponentExt(AcroVersionExt):
    """
    A custom component extension with version tracking.
    Inherits tox management from AcroToxExt via AcroVersionExt.
    """

    def __init__(self, ownerComp, logger, **kwargs):
        super().__init__(ownerComp, logger, **kwargs)
        # Additional initialization for your component here.

    def PostInit(self):
        """Called after all extensions have initialized."""
        super().PostInit()
        # Check for updates on startup.
        self.CheckForUpdates()

    def OnPulse(self, par):
        """Handle custom pulse parameters."""
        if par.name == 'Checkforupdates':
            self.CheckForUpdates()
        elif par.name == 'Bumpversion':
            self.PromptVersionBump()
        else:
            super().OnPulse(par)
```

After attaching this extension to a component, the component will have:

- A **Tox** parameter page (from `AcroToxExt`) for tox file management.
- A **Version** parameter page (from `AcroVersionExt`) for version tracking.
- Both `tox_managed` and `version_tracking` tags for discovery.

---

## Tag Discovery

Every component using `AcroVersionExt` is tagged with **two** tags:

| Tag | Source | Purpose |
|-----|--------|---------|
| `tox_managed` | `AcroToxExt` (parent class) | Identifies the component as a managed tox, discoverable by the tox management system. |
| `version_tracking` | `AcroVersionExt` (`VERSION_TAG = 'version_tracking'`) | Identifies the component as version-tracked, enabling targeted version queries and batch update operations. |

You can discover all version-tracked components in a project using tag-based search:

```python
# Find all version-tracked components in the project.
version_tracked = root.findChildren(tags=['version_tracking'])

# Find all tox-managed components (includes version-tracked ones).
tox_managed = root.findChildren(tags=['tox_managed'])

# Find components that are version-tracked (always also tox-managed).
for comp in version_tracked:
    print(comp.name, comp.par.Version, comp.par.Build)
```

Because `AcroVersionExt` inherits from `AcroToxExt`, every component with the `version_tracking` tag is guaranteed to also have the `tox_managed` tag. The reverse is not true — a component may be tox-managed without version tracking.
