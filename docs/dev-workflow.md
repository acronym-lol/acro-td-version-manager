---
last_reviewed: 2026-08-27
sidebar_label: 'Dev Workflow'
---

# Development Workflow

## Overview

The Acro TD Core provides an integrated development workflow that automates version management, changelog generation, and component saving. When **Dev Mode** is active, saving your project triggers a series of automated steps: a version bump dialog, changelog updates, tox file saves, and dirty component management. This system is designed so that developers working within a component's own repository get a streamlined edit-save-commit cycle with minimal manual bookkeeping.

The workflow revolves around three key systems:

- **Dev Mode** controls whether development automation is active.
- **Version Bump Flow** prompts for semantic version increments on save.
- **Save-on-Save Modes** determine how each tox-managed component is persisted.

---

## Dev Mode

Dev Mode is controlled by the `AcroVersionExt.Devmode` parameter, which provides a menu with three options:

| Value    | Label              | Behavior                                  |
|----------|--------------------|-------------------------------------------|
| `off`    | Disabled           | Dev features are never active.            |
| `auto`   | Auto (In Repo)     | Dev features activate only when the project is open inside its own repository. |
| `always` | Always             | Dev features are always active regardless of project location. |

### How activation is determined

The internal method `_isDevActive()` evaluates the current mode:

```python
def _isDevActive(self):
    if self.Devmode == 'off':
        return False
    elif self.Devmode == 'auto':
        return self.IsInRepo
    elif self.Devmode == 'always':
        return True
```

### IsInRepo

The `IsInRepo` property on `AcroToxExt` compares the current project folder against the configured `Repopath`:

```python
@property
def IsInRepo(self):
    return os.path.normpath(project.folder) == os.path.normpath(self.Repopath)
```

This returns `True` when you are editing the component from within its own repository, which is the expected scenario during active development.

### When to use each mode

- **Disabled** -- Use when you are consuming a component as a dependency in another project and do not want save operations to trigger version prompts.
- **Auto (In Repo)** -- The recommended default. Dev features activate only when the project folder matches the component's repository path, preventing accidental version bumps when the component is used elsewhere.
- **Always** -- Use when you need dev features regardless of project location, for example when developing against a symlinked or non-standard folder structure.

---

## Version Bump Flow

When a project save occurs and Dev Mode is active, `PromptVersionBump` in `AcroVersionExt` runs the following sequence:

### Step 1: Check Dev Mode

The method first calls `_isDevActive()`. If it returns `False`, the entire bump flow is skipped.

### Step 2: Extract the build number

The new build number is read from the project filename using `GetBuildNumberFromProjectName()`:

```python
def GetBuildNumberFromProjectName(self):
    # TouchDesigner project name format: 'ProjectName.246.toe'
    parts = project.name.split('.')
    return parts[-2]  # Returns '246'
```

### Step 3: Check dirty state and prompt

If the component `IsDirty` (or the `Onlybumpdirty` toggle is off), a dialog is presented to the user:

```
Current version: v1.6.1.245
New build: 246
Would you like to bump the semantic version?
```

The dialog offers five buttons:

| Button         | Action                                                                              | Example              |
|----------------|-------------------------------------------------------------------------------------|----------------------|
| **Major**      | Increments major version, resets minor and patch. Updates CHANGELOG.                | `1.6.1` -> `2.0.0`  |
| **Minor**      | Increments minor version, resets patch. Updates CHANGELOG.                          | `1.6.1` -> `1.7.0`  |
| **Patch**      | Increments patch version. Updates CHANGELOG.                                        | `1.6.1` -> `1.6.2`  |
| **Build**      | Saves with the new build number only — no semantic bump, no CHANGELOG entry.        | `1.6.1.245` -> `1.6.1.246` |
| **Don't Save** | Skips everything. The component remains dirty and no version data is written.       | unchanged            |

### Step 4: Update version file and parameters

If the user picked anything other than **Don't Save**, the following are always updated:

- The version file on disk
- The `version` parameter
- The `build` parameter (set to the new build number)
- The `td_version` parameter
- The `td_build` parameter

### Step 5: Update changelog (conditional)

If a semantic bump occurred (Major, Minor, or Patch), the changelog is updated. See the [Changelog Generation](#changelog-generation) section below. **Build** does not generate a CHANGELOG entry.

### Step 6: Auto-save the tox

Finally, the tox file is saved automatically without prompting:

```python
self.SaveTox(prompt=False)
```

### Skip-when-clean and Force Bump

Two parameters fine-tune the prompt:

| Parameter | Behavior |
|-----------|----------|
| `Onlybumpdirty` (default on) | When on, the prompt is skipped if the component is clean. When off, the prompt fires on every save — useful for project-level scene tracking. |
| `Forcebump` (pulse) | Calls `PromptVersionBump(force=True)`. Bypasses both the dev-mode gate and the dirty check. Wired to a UI button on the Version page. |

---

## Build Numbers

TouchDesigner automatically increments a build number in the project filename each time you save. The filename follows the format:

```
ProjectName.246.toe
```

The `GetBuildNumberFromProjectName()` method extracts this number by splitting the filename on `.` and taking the second-to-last element:

```python
def GetBuildNumberFromProjectName(self):
    parts = project.name.split('.')
    return parts[-2]
```

For the filename `MyProject.246.toe`, the parts are `['MyProject', '246', 'toe']`, and `parts[-2]` yields `'246'`.

This build number is stored alongside the semantic version to provide a monotonically increasing identifier that tracks every individual save, independent of whether a semantic version bump occurred.

---

## Changelog Generation

The `UpdateChangelog` method in `AcroVersionExt` manages the `CHANGELOG.md` file located in the project folder.

### File creation

If `CHANGELOG.md` does not yet exist, it is created automatically.

### Entry format

Each version entry follows this format:

```markdown
## [1.7.0] - 2026-02-20
-
```

The entry includes the new semantic version in brackets, followed by the current date in `YYYY-MM-DD` format, and a blank bullet point for the developer to fill in.

### Insertion logic

New entries are inserted before the first existing version entry in the file. This keeps the changelog in reverse chronological order with the most recent version at the top.

### Post-update behavior

After writing the changelog, the file is opened in the system's default text editor:

```python
# Windows
os.startfile(changelog_path)

# macOS
subprocess.call(['open', changelog_path])
```

This allows the developer to immediately add release notes for the new version.

---

## Save-on-Save Modes

Each tox-managed component has an `Onsave` parameter on `AcroToxExt` that controls what happens to that component when the project is saved. There are four modes:

| Value    | Behavior                                                                 |
|----------|--------------------------------------------------------------------------|
| `off`    | The component's tox file is never saved when the project saves.         |
| `prompt` | A dialog is shown asking whether to save the component's tox file.      |
| `always` | The component's tox file is saved automatically without any prompt.     |
| `auto`   | The component's tox file is saved automatically, but only if the project is currently open inside the component's own repository (`IsInRepo` is `True`). |

### Choosing a mode

- **off** -- Use for components that are read-only dependencies or should not be modified in the current project context.
- **prompt** -- Use when you want explicit control over which components are saved on each project save. Good for projects with many components where only some are actively being edited.
- **always** -- Use for components that should always be persisted. Suitable for the primary component in a single-component project.
- **auto** -- The recommended default for most components. It prevents accidental overwrites when a component is used outside its home repository, while providing frictionless saves when you are working in the correct repo.

---

## Project Save Lifecycle

When you save the project (File > Save), two systems execute in sequence: the project-level save handler and the version manager.

### AcroCore.onSave

The project-level save callback runs the following steps in order:

```python
def onSave(self):
    self.PromptVersionBump()      # 1. Prompt for version bump if dev mode active
    self.createDefaultFolders()   # 2. Ensure required folders exist
    self.createGitIgnore()        # 3. Copy .gitignore template if missing
```

1. **PromptVersionBump()** -- Runs the full [Version Bump Flow](#version-bump-flow) described above. If Dev Mode is not active, this step is a no-op.
2. **createDefaultFolders()** -- Creates any default project folders that the template expects but that may not yet exist on disk.
3. **createGitIgnore()** -- If no `.gitignore` file exists in the project folder, copies the template `.gitignore` into place.

### AcroVersionManager.onSaveStart

The version manager's save handler runs after the project-level save:

```python
def onSaveStart(self):
    if self.Checkdirtyonsave:
        self.PromptSaveDirtyComponents()
```

1. **Check the Checkdirtyonsave flag** -- If this parameter is disabled, no further action is taken.
2. **PromptSaveDirtyComponents()** -- Finds all tox-managed components that are marked as dirty and whose `Onsave` mode is not `off`.
3. **Per-component handling** -- Each qualifying component's `PromptSaveTox()` method is called, which behaves according to that component's own `Onsave` setting:
   - `prompt`: shows a save dialog for that component.
   - `always`: saves the tox immediately.
   - `auto`: saves the tox only if `IsInRepo` is `True`.

---

## Typical Dev Cycle

A complete development cycle proceeds through the following steps:

1. **Open the project** in TouchDesigner. If Dev Mode is set to `auto`, dev features will activate automatically when the project folder matches the repository path.

2. **Edit components** within TouchDesigner as needed. Modified components are tracked internally as dirty.

3. **Save the project** via File > Save (or Ctrl+S). This triggers the full save lifecycle.

4. **Version bump dialog appears** (if Dev Mode is active and the component is dirty). The dialog shows the current version and the new build number extracted from the project filename.

5. **Choose a version bump type**:
   - Select **Major**, **Minor**, or **Patch** for a semantic version increment.
   - Select **Skip** to keep the current version and only update the build number.

6. **Version file and parameters are updated** with the new version, build number, TouchDesigner version, and TouchDesigner build.

7. **Changelog is updated** (only if a semantic bump was selected). The `CHANGELOG.md` file opens in your default editor for you to add release notes.

8. **Tox is auto-saved** without prompting, persisting the component to its `.tox` file.

9. **Dirty components are processed** by the version manager. Each component with a compatible `Onsave` mode is saved or prompted according to its configuration.

10. **Commit changes to git**. With the version file, changelog, and tox files all updated on disk, you can stage and commit your changes:

```bash
git add -A
git commit -m "v1.7.0 - description of changes"
```

This cycle ensures that every save produces a consistent, versioned, and documented snapshot of your project state, ready for version control.
