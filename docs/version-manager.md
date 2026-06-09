# AcroVersionManager

## Overview

`AcroVersionManager` is the central manager responsible for tracking, reporting, and updating versioned components within a TouchDesigner project. It extends `CallbacksExt` and operates as a singleton service that discovers components tagged for version tracking, compares their current versions against available remote versions, and provides mechanisms for updating, skipping, or ignoring updates.

The manager integrates with the project lifecycle, optionally checking for updates on project start and prompting to save dirty tox-managed components on project save. All persistent state -- skipped versions and ignored components -- is maintained through `StorageManager`, ensuring settings survive between sessions.

## Component Discovery

AcroVersionManager discovers components using two tag constants:

- **`VERSION_TAG`** (`'version_tracking'`) -- Identifies components that participate in version tracking. These components are expected to expose version metadata that the manager can compare against remote sources.
- **`TOX_TAG`** (`'tox_managed'`) -- Identifies components managed as tox files. These components are monitored for unsaved changes (dirty state).

Discovery is performed by searching from the project root downward:

```python
def _getVersionedComponents(self):
    return root.findChildren(tags=[VERSION_TAG])

def _getToxComponents(self):
    return root.findChildren(tags=[TOX_TAG])
```

Any component in the project hierarchy that carries the appropriate tag will be automatically discovered by the manager. No manual registration is required.

## Manager Parameters

The following parameters are exposed on the `AcroVersionManager` component itself and control its runtime behavior:

| Parameter | Type | Description |
|---|---|---|
| `Checkonstart` | toggle | Check for updates automatically when the project starts. |
| `Startupdelay` | int | Delay in frames before the startup check executes. |
| `Printtotextport` | toggle | Print version status results to the textport. |
| `Showpopup` | toggle | Show a popup dialog when updates are available. |
| `Automaticupdates` | toggle | Enable automatic update functionality for components that support it. |
| `Checkdirtyonsave` | toggle | Check for unsaved (dirty) tox-managed components when the project is saved. |
| `Callbackdat` | DAT | Reference to the callback DAT used by the `CallbacksExt` base class. |

## Core Methods

### CheckAll

`CheckAll()` is the primary entry point for scanning all versioned components. It performs a full scan, optionally prints a report and shows a popup dialog, and returns the list of available updates.

```python
def CheckAll(self):
    updates = self._scanForUpdates()
    if self.ownerComp.par.Printtotextport:
        self._printReport(updates)
    if self.ownerComp.par.Showpopup:
        self._showUpdateDialog(updates)
    return updates
```

The returned `updates` list contains entries for each component that has a newer version available, excluding any components or versions that have been skipped or ignored.

### PrintReport

`PrintReport()` prints a formatted version status report for all versioned components to the textport. This includes both up-to-date and outdated components.

```python
def PrintReport(self):
    updates = self._scanForUpdates()
    self._printReport(updates)
```

### ClearIgnored

`ClearIgnored()` resets all stored skip and ignore preferences, re-enabling update checks for every component and every version.

```python
def ClearIgnored(self):
    self.SkippedVersions = {}
    self.IgnoredComponents = []
```

Both `SkippedVersions` and `IgnoredComponents` are cleared from persistent storage, so subsequent calls to `CheckAll` will report all available updates.

## Skip/Ignore System

AcroVersionManager provides two levels of suppression for update notifications:

### SkipVersion

`SkipVersion(comp, version)` marks a specific version as skipped for a given component. The component will continue to be checked for updates, but the specified version will not appear in future reports.

```python
def SkipVersion(self, comp, version):
    self.SkippedVersions[comp.path] = version
```

This is useful when a particular release is known to be incompatible or undesirable, but future versions should still be reported.

### IgnoreComponent

`IgnoreComponent(comp)` suppresses all update notifications for a component entirely. The component will be excluded from all future scans until it is explicitly un-ignored.

```python
def IgnoreComponent(self, comp):
    self.IgnoredComponents.append(comp.path)
```

### UnignoreComponent

`UnignoreComponent(comp)` re-enables update checking for a previously ignored component.

```python
def UnignoreComponent(self, comp):
    self.IgnoredComponents.remove(comp.path)
```

### How _scanForUpdates Uses These

During a scan, `_scanForUpdates()` iterates over all discovered versioned components and applies the following logic:

1. If the component's path is in `IgnoredComponents`, it is skipped entirely.
2. If the component's path is in `SkippedVersions` and the available remote version matches the skipped version, that update is excluded from the results.
3. All remaining components with available updates are included in the returned list.

## Update Management

### UpdateComponent

`UpdateComponent(comp, remote_version)` triggers an update for a single component. The update only proceeds if `Automaticupdates` is enabled on the manager and the component implements a `PerformUpdate` method.

```python
def UpdateComponent(self, comp, remote_version):
    if self.ownerComp.par.Automaticupdates:
        if hasattr(comp, 'PerformUpdate'):
            comp.PerformUpdate(remote_version)
```

The actual update logic is delegated to the component itself. AcroVersionManager does not prescribe how updates are applied -- it only orchestrates the process.

### UpdateAll

`UpdateAll(updates)` iterates over a list of update entries (as returned by `CheckAll` or `_scanForUpdates`) and calls `UpdateComponent` for each one that supports automatic updates.

```python
def UpdateAll(self, updates):
    for update in updates:
        self.UpdateComponent(update['comp'], update['remote_version'])
```

Components that do not implement `PerformUpdate` are silently skipped.

## Dirty Tox Management

AcroVersionManager monitors tox-managed components for unsaved changes, providing a safety net before project saves.

### GetDirtyComponents

`GetDirtyComponents()` finds all tox-managed components (tagged with `TOX_TAG`) that have unsaved modifications and whose `Onsave` parameter is not set to `'off'`.

```python
def GetDirtyComponents(self):
    dirty = []
    for comp in self._getToxComponents():
        if comp.par.Onsave != 'off' and comp.dirty:
            dirty.append(comp)
    return dirty
```

A component is considered "dirty" if it has been modified since its last save.

### PromptSaveDirtyComponents

`PromptSaveDirtyComponents()` iterates over all dirty components and calls each component's own `PromptSaveTox()` method, allowing the user to decide whether to save each one.

```python
def PromptSaveDirtyComponents(self):
    dirty = self.GetDirtyComponents()
    for comp in dirty:
        comp.PromptSaveTox()
```

This is typically triggered automatically during the project save lifecycle when `Checkdirtyonsave` is enabled.

## Lifecycle Hooks

AcroVersionManager hooks into two key project lifecycle events:

### onStart

Called when the project starts. If `Checkonstart` is enabled, it schedules a `CheckAll` call after the configured `Startupdelay` (in frames).

```python
def onStart(self):
    if self.ownerComp.par.Checkonstart:
        run("args[0]()", self.CheckAll, delayFrames=self.ownerComp.par.Startupdelay)
```

The delay allows the project to fully initialize before the version scan begins, avoiding issues with components that are not yet ready.

### onSaveStart

Called when the project begins saving. If `Checkdirtyonsave` is enabled, it runs `PromptSaveDirtyComponents()` to give the user a chance to save any modified tox files before the project save completes.

```python
def onSaveStart(self):
    if self.ownerComp.par.Checkdirtyonsave:
        self.PromptSaveDirtyComponents()
```

### Pulse Handlers

Three pulse parameters are available for manual triggering:

| Pulse Parameter | Action |
|---|---|
| `pulse_Checkall` | Calls `CheckAll()` |
| `pulse_Printreport` | Calls `PrintReport()` |
| `pulse_Clearignored` | Calls `ClearIgnored()` |

These allow operators to trigger version management actions directly from the parameter interface without writing scripts.

## Persistent Storage

AcroVersionManager uses `StorageManager` to persist two data structures across project sessions:

### SkippedVersions

A dictionary mapping component paths to version strings. When a user skips a particular version for a component, the entry is stored here.

```python
# Structure
SkippedVersions = {
    '/project1/components/myComp': '1.2.0',
    '/project1/tools/otherComp': '2.0.0-beta',
}
```

When `_scanForUpdates` encounters a component whose path is a key in this dictionary and the remote version matches the stored value, that update is excluded from the results.

### IgnoredComponents

A list of component paths that should be completely excluded from version checking.

```python
# Structure
IgnoredComponents = [
    '/project1/components/stableComp',
    '/project1/legacy/oldComp',
]
```

Components whose paths appear in this list are skipped entirely during `_scanForUpdates`.

Both storage entries are managed through `StorageManager`, which handles serialization and persistence automatically. Calling `ClearIgnored()` resets both to their empty defaults.

## Update Dialog

When `Showpopup` is enabled and updates are found, `_showUpdateDialog(updates)` presents a `messageBox` dialog to the user. The dialog displays the list of available updates and offers three action buttons:

| Button | Action |
|---|---|
| **Dismiss** | Closes the dialog without taking any action. Updates will be reported again on the next check. |
| **Skip All** | Calls `SkipVersion` for each update in the list, recording the specific versions so they will not be reported again. Future versions will still be reported. |
| **Ignore All** | Calls `IgnoreComponent` for each component with an available update, suppressing all future update notifications for those components. |

```python
def _showUpdateDialog(self, updates):
    # Constructs a formatted message listing all available updates
    # Displays via ui.messageBox with Dismiss / Skip All / Ignore All buttons
    # Processes the user's choice accordingly
    pass
```

The dialog is non-blocking in the sense that the project continues to run while it is displayed, but the user must interact with it before it is dismissed. Selecting **Skip All** or **Ignore All** writes to the persistent storage immediately, so the preferences take effect on subsequent scans without requiring a project restart.
