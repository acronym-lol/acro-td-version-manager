# AcroToxExt - External Tox Management

## Overview

`AcroToxExt` is a mixin class that provides standardized external tox file management for TouchDesigner components. It creates a unified interface for saving, loading, and synchronizing `.tox` files with TouchDesigner's built-in external tox system.

Use `AcroToxExt` when you need to:

- Manage a component's external tox file through custom parameters rather than TD's native interface.
- Automatically save tox files on project save with configurable behavior (disabled, prompt, always, auto).
- Bind custom parameter controls to TD's built-in `externaltox` and `enableexternaltox` parameters via expressions.
- Discover all managed components at runtime through the `tox_managed` tag.
- Support repository-aware auto-save workflows where tox files are only saved when the project is running from within the component's designated repo folder.

The mixin automatically creates a **Component** parameter page on the owner component, adds the `tox_managed` tag for discovery, and binds its custom parameters to TD's native external tox system.

---

## Component Parameter Page

When `AcroToxExt.__init__` runs, it ensures a **Component** parameter page exists on the owner component with the following parameters:

| Name | Label | Type | Default | Description | Enable Condition |
|------|-------|------|---------|-------------|------------------|
| `Repopath` | Repository Folder | `folder` | `''` | Git repo folder for this component. Used by auto-save mode to determine if the project is running from within the expected repository. | Always enabled |
| `Enableexternaltox` | Enable External Tox | `toggle` | `False` | Enable external tox loading. Syncs with TD's built-in `enableexternaltox` parameter via expression binding. | Always enabled |
| `Externaltoxpath` | External Tox Path | `file` | `''` | Path to the external tox file on disk. Syncs with TD's built-in `externaltox` parameter via expression binding. | `me.par.Enableexternaltox` |
| `Onsave` | Save on Project Save | `menu` | `off` | Controls how tox saving is handled when the TouchDesigner project saves. Options: Disabled / Prompt to Save / Always Save / Auto (In Repo). | `me.par.Enableexternaltox` |
| `Reloadtox` | Reload Tox | `pulse` | N/A | Pulse to reload the external tox file from disk. Triggers `ReloadTox()`. | `me.par.Enableexternaltox` |
| `Reloadcustom` | Reload Custom Parameters | `toggle` | `True` | When enabled, custom parameters are reloaded when the tox is reloaded from disk. | `me.par.Enableexternaltox` |
| `Reloadbuiltin` | Reload Built-In Parameters | `toggle` | `True` | When enabled, built-in parameters are reloaded when the tox is reloaded from disk. | `me.par.Enableexternaltox` |

The parameters are organized into two sections on the Component page:

- **External Tox** section (starting at `Enableexternaltox`) -- controls for enabling and configuring the external tox file.
- **Reload** section (starting at `Reloadtox`) -- controls for reloading the tox from disk.

---

## TD Parameter Binding

`AcroToxExt` binds its custom parameters to TouchDesigner's built-in external tox parameters using **expression mode**. This means TD's native parameters are driven by the custom parameters at all times, keeping the two in sync without manual intervention.

The bindings are established in `_bindExternalToxParams()`:

```python
# TD's built-in externaltox is driven by our custom Externaltoxpath
comp.par.externaltox.expr = "me.par.Externaltoxpath"

# TD's built-in enableexternaltox is driven by our custom Enableexternaltox
comp.par.enableexternaltox.expr = "me.par.Enableexternaltox"
```

Both bindings use **EXPRESSION mode**, meaning the built-in parameters evaluate the expression each frame. When you change `Externaltoxpath` or `Enableexternaltox` on the Component page, TD's native parameters update automatically.

> **Important:** Because expression mode is used, you should not manually set TD's built-in `externaltox` or `enableexternaltox` parameters directly. Always use the custom parameters on the Component page to avoid conflicts.

---

## Save Modes

The `Onsave` parameter controls what happens when `PromptSaveTox()` is called (typically triggered on project save). There are four modes:

| Menu Value | Label | Behavior |
|------------|-------|----------|
| `off` | Disabled | Tox is never saved on project save. `PromptSaveTox()` returns `False` immediately. |
| `prompt` | Prompt to Save | A message box dialog is shown asking the user whether to save the tox. The user can confirm or cancel. |
| `always` | Always Save | The tox is saved automatically without any prompt every time the project saves. |
| `auto` | Auto (In Repo) | The tox is saved automatically **only** if the project is currently running from within the component's repository folder. If not in the repo, save is skipped silently. |

### PromptSaveTox Logic

The `PromptSaveTox()` method implements the following decision flow:

```python
def PromptSaveTox(self):
    # 1. If saving is disabled, do nothing
    if self.Onsave == 'off':
        return False

    # 2. If the component is not dirty, skip saving
    if not self.IsDirty:
        return False

    # 3. Handle each mode
    if self.Onsave == 'auto':
        # Only save if project folder matches the repo path
        if not self.IsInRepo:
            return False
        return self.SaveTox(prompt=False)

    elif self.Onsave == 'always':
        return self.SaveTox(prompt=False)

    elif self.Onsave == 'prompt':
        return self.SaveTox(prompt=True)
```

### Auto Mode and IsInRepo

The `auto` mode relies on the `IsInRepo` property to determine whether saving should proceed. This property compares the current TouchDesigner project folder against the `Repopath` parameter:

```python
@property
def IsInRepo(self):
    return os.path.normpath(project.folder) == os.path.normpath(self.Repopath)
```

This comparison uses `os.path.normpath` to handle differences in trailing slashes, mixed separators, and other path formatting inconsistencies.

**When to use auto mode:** Auto mode is ideal for components that are developed in a specific repository but also used (via tox) in other projects. When the component is loaded in the development repo, changes are saved automatically. When the same component is loaded in a different project, saves are skipped, preventing accidental overwrites.

---

## Properties Reference

All properties are read-only and provide access to the current state of the tox management system.

| Property | Type | Description |
|----------|------|-------------|
| `IsDirty` | `bool` | Whether the owner component has unsaved changes. Returns `self._toxOwnerComp.dirty`. |
| `Enableexternaltox` | `bool` | Current value of the Enable External Tox toggle parameter. |
| `Externaltoxpath` | `str` | Current value of the External Tox Path file parameter. |
| `Onsave` | `str` | Current save mode. One of `'off'`, `'prompt'`, `'always'`, or `'auto'`. |
| `Repopath` | `str` | Current value of the Repository Folder parameter. |
| `IsInRepo` | `bool` | Whether the current project folder matches the configured repository path (normalized comparison). |
| `Reloadcustom` | `bool` | Whether custom parameters should be reloaded when reloading the tox. |
| `Reloadbuiltin` | `bool` | Whether built-in parameters should be reloaded when reloading the tox. |

---

## Methods Reference

| Method | Arguments | Returns | Description |
|--------|-----------|---------|-------------|
| `GetToxSavePath()` | None | `str` | Returns the save path for the tox file. If `Externaltoxpath` is set, returns that path. Otherwise, returns a default path constructed as `project.folder/tox/[componentName].tox`. |
| `ReloadTox()` | None | `bool` | Reloads the tox from disk by pulsing `comp.par.reinitnet` with `loadCustom` and `loadBuiltIn` flags set according to the `Reloadcustom` and `Reloadbuiltin` parameters. Returns `True` on success, `False` on failure. |
| `SaveTox(path, prompt)` | `path=None` (`str` or `None`), `prompt=True` (`bool`) | `bool` | Saves the component as a tox file. If `path` is `None`, uses `GetToxSavePath()`. If `prompt` is `True`, displays a confirmation dialog via `ui.messageBox` before saving. On successful save, updates `Externaltoxpath` and `Enableexternaltox` if they are not already set. Returns `True` on success, `False` on failure or cancellation. |
| `PromptSaveTox()` | None | `bool` | Evaluates the current `Onsave` mode and dirty state to determine whether and how to save. See the [Save Modes](#save-modes) section for the full decision logic. Returns `True` if the tox was saved, `False` otherwise. |
| `pulse_Reloadtox()` | None | None | Callback triggered when the `Reloadtox` pulse parameter is pressed. Delegates to `ReloadTox()`. |

---

## Usage Example

To add tox management to a custom extension, inherit from `AcroToxExt` and call its `__init__` in your constructor:

```python
from AcroToxExt import AcroToxExt

class MyComponent(AcroToxExt):
    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        AcroToxExt.__init__(self, ownerComp)
        # Your own initialization here

    def OnProjectSave(self):
        """Called by TD when the project is about to save."""
        self.PromptSaveTox()

    def OnCustomPulse(self, par):
        """Handle pulse parameter callbacks."""
        if par.name == 'Reloadtox':
            self.pulse_Reloadtox()
```

After initialization, the Component parameter page is available on the owner component. Users can configure the external tox path and save behavior through the parameter dialog.

### Saving a Tox Programmatically

```python
# Save to the configured path without prompting
comp.ext.MyComponent.SaveTox(prompt=False)

# Save to a specific path with a confirmation dialog
comp.ext.MyComponent.SaveTox(path='/path/to/output.tox', prompt=True)

# Get the resolved save path without saving
save_path = comp.ext.MyComponent.GetToxSavePath()
```

### Reloading a Tox Programmatically

```python
# Reload from disk, respecting Reloadcustom and Reloadbuiltin settings
comp.ext.MyComponent.ReloadTox()
```

---

## Tag Discovery

When `AcroToxExt.__init__` runs, it adds the `tox_managed` tag to the owner component via `_ensureToxTag()`. This tag can be used to discover all components in a project that use the tox management system.

```python
# Find all tox-managed components in the project
managed_comps = root.findChildren(tags=[TOX_TAG])

# Iterate and check dirty state
for comp in managed_comps:
    if comp.dirty:
        print(f'{comp.path} has unsaved changes')
```

The tag constant is defined at module level:

```python
TOX_TAG = 'tox_managed'
```

This enables workflows such as:

- **Batch saving:** Iterate all managed components and call `PromptSaveTox()` on each during a project save event.
- **Status dashboards:** Build a UI that lists all managed components with their dirty state and external tox paths.
- **CI/CD integration:** Programmatically export all managed tox files from a project.

The tag is added idempotently -- calling `_ensureToxTag()` multiple times will not create duplicate tags.
