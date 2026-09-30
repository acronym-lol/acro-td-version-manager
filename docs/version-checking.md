---
last_reviewed: 2026-08-27
sidebar_position: 4
---

# Remote Version Checking

## Overview

The remote version checking system allows a TouchDesigner project to compare its local version against a remote source and determine whether an update is available. The system is implemented in `AcroVersionExt` and supports two methods for retrieving the remote version:

1. **HTTP URL method** -- fetches a JSON version file from a raw URL (e.g., GitHub).
2. **Git fetch method** -- uses local Git commands to read the version file from the remote branch.

The HTTP URL method is the primary approach. The Git fetch method serves as a fallback when no URL is configured but a local repository path is available.

After fetching the remote version, the system performs a semantic version comparison and, optionally, a build number comparison to determine whether the local project is outdated, up to date, or ahead of the remote.

---

## HTTP URL Method

The HTTP URL method retrieves a version file directly from a remote server using `urllib.request`.

### Setup

Set the `Versionurl` parameter on the version-checking component to the raw URL of your version file. For GitHub-hosted projects, this is the raw content URL:

```
https://raw.githubusercontent.com/{user}/{repo}/{branch}/version.json
```

For example:

```
https://raw.githubusercontent.com/myorg/myproject/main/version.json
```

### How It Works

When `GetRemoteVersion` is called and `Versionurl` is set, the system:

1. Constructs an HTTP request to the URL.
2. If token authentication is enabled (`Usetoken` is on and `Token` is set), adds an `Authorization` header.
3. Fetches the response and parses the returned JSON.

```python
import urllib.request
import json

url = op('versioncheck').par.Versionurl.eval()
request = urllib.request.Request(url)

# Optional token authentication
if op('versioncheck').par.Usetoken.eval() and op('versioncheck').par.Token.eval():
    token = op('versioncheck').par.Token.eval()
    request.add_header('Authorization', f'token {token}')

response = urllib.request.urlopen(request)
data = json.loads(response.read().decode())
```

The version file should be a JSON document containing at minimum a version string and optionally a build number.

---

## Git Fetch Method

The Git fetch method is used as a fallback when `Versionurl` is empty but `Repopath` is set to a local Git repository directory.

### How It Works

1. The system runs `git fetch` in the repository directory to update remote tracking branches.
2. It reads the version file from the remote branch using `git show`.
3. The path to the version file within the repository is computed using `os.path.relpath` against the `Versionfile` parameter.

### Branch Fallback Order

The system attempts to read the version file from the remote in the following order:

```python
git show origin/HEAD:{relative_path}
```

If that fails, it falls back to:

```python
git show origin/main:{relative_path}
```

If that also fails, it falls back to:

```python
git show origin/master:{relative_path}
```

This fallback chain ensures compatibility with repositories using either `main` or `master` as their default branch, as well as repositories where `origin/HEAD` is properly configured.

### Path Resolution

The `Versionfile` parameter specifies the absolute path to the local version file. The system computes the repo-relative path using:

```python
import os

relative_path = os.path.relpath(version_file_path, repo_path)
```

This relative path is then passed to `git show` to retrieve the corresponding file from the remote branch.

---

## Token Authentication

Token authentication is required when the version file is hosted in a private GitHub repository. The system uses a GitHub fine-grained Personal Access Token (PAT).

### Creating a Fine-Grained PAT

1. Go to **GitHub > Settings > Developer settings > Personal access tokens > Fine-grained tokens**.
2. Click **Generate new token**.
3. Set the token name and expiration as desired.
4. Under **Repository access**, select **Only select repositories** and choose the specific repository.
5. Under **Permissions > Repository permissions**, set **Contents** to **Read-only**. No other permissions are needed.
6. Click **Generate token** and copy the resulting token string.

### Configuration

Three parameters control token authentication:

| Parameter  | Description                                      |
|------------|--------------------------------------------------|
| `Usetoken` | Toggle to enable or disable token authentication |
| `Token`    | The GitHub fine-grained Personal Access Token     |

When both `Usetoken` is enabled and `Token` has a value, the HTTP request includes the following header:

```python
request.add_header('Authorization', f'token {TOKEN}')
```

If `Usetoken` is off or `Token` is empty, the request is made without authentication. This is sufficient for public repositories.

### Security Notes

- The token only requires **Contents** read-only permission on the specific repository.
- Do not commit tokens to version control. Store them in environment variables or parameter overrides that are excluded from commits.
- Fine-grained tokens can be scoped to a single repository, limiting exposure if the token is compromised.

---

## Version Comparison

The `CompareVersions` method handles semantic version comparison between local and remote version strings.

### Parsing

Version strings follow the `major.minor.patch` format (e.g., `"1.6.1"`). The method:

1. Splits the version string on `"."`.
2. Converts each part to an integer.
3. Pads the result to exactly 3 parts (major, minor, patch) if fewer are provided.

```python
# Example: "1.6" becomes [1, 6, 0]
# Example: "1.6.1" becomes [1, 6, 1]
# Example: "2" becomes [2, 0, 0]
```

### Comparison Result

The method returns an integer:

| Return Value | Meaning                          |
|--------------|----------------------------------|
| `1`          | Local version is greater than remote |
| `-1`         | Local version is less than remote    |
| `0`          | Versions are equal                   |

Parts are compared left to right (major, then minor, then patch). The first non-equal part determines the result.

```python
# CompareVersions("1.6.1", "1.6.0") returns 1   (local > remote)
# CompareVersions("1.5.0", "1.6.0") returns -1  (local < remote)
# CompareVersions("1.6.1", "1.6.1") returns 0   (equal)
```

---

## Update Detection Flow

The `HasUpdate` method orchestrates the full update detection process. It returns a tuple: `(has_update, remote_info)`.

### Skip Conditions

The check is skipped entirely (returns no update) when either of the following is true:

- **Dev mode is active** -- the project is in a development state and version checks are not meaningful.
- **Version checking is disabled** -- the version checking feature has been turned off in the component settings.

### Detection Logic

When the check proceeds:

1. The remote version is fetched using either the HTTP URL method or the Git fetch method.
2. The local and remote semantic version strings are compared using `CompareVersions`.
3. If the semantic versions are **equal**, the build numbers are compared as a tiebreaker.
4. An update is available when the remote version is greater than the local version, or when versions are equal but the remote build number is higher.

```python
has_update, remote_info = version_ext.HasUpdate()

if has_update:
    print(f"Update available: {remote_info}")
else:
    print("No update available")
```

### CheckForUpdates

The `CheckForUpdates` method wraps `HasUpdate` with logging:

1. Calls `HasUpdate` to determine the update status.
2. Logs the results (remote version, comparison outcome).
3. Detects and reports the "local ahead of remote" condition (see below).

---

## Local Ahead of Remote

When the local version is greater than the remote version (or the versions are equal but the local build number is higher), the system considers the local project to be "ahead of remote." This situation is reported differently depending on whether dev mode is active.

### Dev Mode Active

When dev mode is active, the message is informational:

```python
"{comp.path}: Local ahead of remote ({local} > {remote})"
```

This is expected behavior during development -- a developer working on a new version will naturally be ahead of the published remote version.

### Dev Mode Inactive

When dev mode is **not** active, the message is elevated to a warning:

```python
"WARNING: {comp.path}: Local version ({local}) is ahead of remote ({remote})"
```

This warning indicates a potentially unexpected state. A non-development project should generally not have a version higher than the published remote. Possible causes include:

- The remote version file was not updated after a release.
- The local version was manually incremented without publishing.
- The wrong branch or repository URL is configured.

---

## Troubleshooting

### Remote version fetch returns nothing

- **HTTP URL method**: Verify that `Versionurl` is set and the URL is reachable. Open the URL in a browser to confirm it returns valid JSON. For private repositories, ensure `Usetoken` is enabled and `Token` is set with a valid PAT.
- **Git fetch method**: Verify that `Repopath` points to a valid Git repository directory and that the remote is configured. Run `git remote -v` in the repository to confirm.

### Authentication errors (HTTP 401 or 403)

- Confirm the token has not expired.
- Confirm the token has **Contents** read-only permission for the target repository.
- Confirm `Usetoken` is enabled.
- Ensure the token is a fine-grained PAT scoped to the correct repository.

```python
# Test token access manually
import urllib.request

url = "https://raw.githubusercontent.com/user/repo/main/version.json"
request = urllib.request.Request(url)
request.add_header('Authorization', 'token ghp_xxxxxxxxxxxxxxxxxxxx')

try:
    response = urllib.request.urlopen(request)
    print(response.read().decode())
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} {e.reason}")
```

### Git fetch method fails to read version file

- Ensure `git fetch` succeeds by running it manually in the repository directory.
- Check that `origin/HEAD` is set. If not, the system will fall back to `origin/main` and then `origin/master`. You can set it manually:

```python
# In the repository directory
git remote set-head origin --auto
```

- Verify that the `Versionfile` parameter points to the correct local file and that the file exists in the remote branch at the expected relative path.

### Version comparison returns unexpected results

- Confirm both local and remote version strings follow semantic versioning format (`major.minor.patch`).
- Strings with fewer than 3 parts are padded with zeros. For example, `"1.6"` is treated as `"1.6.0"`.
- Build numbers are only compared when semantic versions are equal. If the semantic version differs, the build number is not a factor.

### "Local ahead of remote" warning in production

- This warning appears when the local version exceeds the remote version and dev mode is not active.
- Verify that the remote version file reflects the latest release.
- Verify that `Versionurl` or the Git remote points to the correct branch (typically `main` or `master`).
- If the local project is intentionally ahead (e.g., a staged release), enable dev mode to suppress the warning.

### Version checks are skipped

- Version checks are skipped when dev mode is active or when version checking is disabled.
- To run checks during development, temporarily disable dev mode or call `GetRemoteVersion` directly.
