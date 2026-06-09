"""
AcroVersionExt - Mixin class for version tracking in TouchDesigner components.

Inherits from AcroToxExt for external tox file management.

Usage:
    class MyExtension(AcroVersionExt):
        def __init__(self, ownerComp):
            AcroVersionExt.__init__(self, ownerComp)
            # ... rest of init

The mixin will automatically create:
    "Component" parameter page (via AcroToxExt):
    - Repopath, Enableexternaltox, Externaltoxpath, Onsave, Reloadtox, Reloadcustom, Reloadbuiltin

    "Version" parameter page:
    - Versionfile: Full path to version file (default: {project.folder}/{comp.name.lower()}-version.json)

    [Version Info]
    - Version, Build, Tdversion, Tdbuild, Lastupdate (read-only)

    [Remote Source]
    - Versionurl: URL to remote version file
    - Usetoken / Token: Auth for private repos

    [Updates]
    - Versioncheckenabled: Check for updates
    - Autoupdate: Auto update mode (off/prompt/always)
    - Reloadonupdate: Reload tox after pulling

    [Development]
    - Devmode: Dev mode menu (off/auto/always)
    - Onlybumpdirty: Skip version bump if component has no changes (default: True)
    - Forcebump: Pulse to manually trigger version bump dialog
"""

import json
import os
import datetime
import subprocess
import urllib.request
import urllib.error

from AcroToxExt import AcroToxExt, TOX_TAG


# Tag used to identify version-tracked components
VERSION_TAG = 'version_tracking'


class AcroVersionExt(AcroToxExt):
    """
    Mixin class for version tracking functionality.
    Inherits tox file management from AcroToxExt.
    Add this to any extension that needs version management.
    """

    def __init__(self, ownerComp):
        self._versionOwnerComp = ownerComp

        # Initialize tox management first (creates Tox page + tox_managed tag)
        AcroToxExt.__init__(self, ownerComp)

        # Ensure Version parameter page exists with all params
        self._ensureVersionPage()

        # Add version tracking tag
        self._ensureVersionTag()

        # Create version file if it doesn't exist
        self._ensureVersionFile()

        # Load version info from file
        self._refreshVersionFromDisk()

    def _ensureVersionTag(self):
        """Ensure the component has the version tracking tag"""
        if VERSION_TAG not in self._versionOwnerComp.tags:
            self._versionOwnerComp.tags.add(VERSION_TAG)

    def _ensureVersionFile(self):
        """Create the version file if it doesn't exist"""
        path = self.Versionfile
        if not path or os.path.exists(path):
            return
        try:
            dir_path = os.path.dirname(path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            data = {
                'version': self.VersionInfo['version'],
                'build': int(self.VersionInfo['build']),
                'last_update': datetime.datetime.now().isoformat(),
                'td_version': self.VersionInfo.get('td_version', ''),
                'td_build': self.VersionInfo.get('td_build', ''),
            }
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Created version file: {path}")
        except Exception as e:
            print(f"Error creating version file: {e}")

    def _ensureVersionPage(self):
        """Create Version parameter page if it doesn't exist"""
        comp = self._versionOwnerComp

        # Check if Version page already exists
        version_page = None
        for page in comp.customPages:
            if page.name == 'Version':
                version_page = page
                break

        # Create page if it doesn't exist
        if version_page is None:
            version_page = comp.appendCustomPage('Version')

        # Define parameters to create
        # Format: (name, label, default, read_only, param_type, help_text, order, enable_expr)
        params = [
            ('Versionfile', 'Version File', '', False, 'file', 'Path to this component version file', 0, None),
            # Version Info
            ('Headerversioninfo', 'Version Info', None, False, 'header', None, 1, None),
            ('Version', 'Version', '1.0.0', True, 'str', 'Semantic version (e.g., 1.0.0)', 2, None),
            ('Build', 'Build', '0', True, 'str', 'Build number', 3, None),
            ('Tdversion', 'TD Version', '', True, 'str', 'TouchDesigner version this was saved with', 4, None),
            ('Tdbuild', 'TD Build', '', True, 'str', 'TouchDesigner build number', 5, None),
            ('Lastupdate', 'Last Updated', '', True, 'str', 'ISO timestamp of last version update', 6, None),
            # Remote Source
            ('Headerremote', 'Remote Source', None, False, 'header', None, 7, None),
            ('Versionurl', 'Remote Version URL', '', False, 'str', 'URL to remote version file for update checking', 8, None),
            ('Usetoken', 'Use Auth Token', False, False, 'toggle', 'Enable token authentication for private repos', 9, None),
            ('Token', 'Auth Token', '', False, 'str', 'GitHub Personal Access Token for private repos', 10, 'me.par.Usetoken'),
            # Updates
            ('Headerupdates', 'Updates', None, False, 'header', None, 11, None),
            ('Versioncheckenabled', 'Check for Updates', True, False, 'toggle', 'Include this component in version checking', 12, None),
            ('Autoupdate', 'Auto Update', 'off', False, 'menu', 'How to handle updates when a new version is found', 13, 'me.par.Versioncheckenabled'),
            ('Reloadonupdate', 'Reload Tox on Update', True, False, 'toggle', 'Reload external tox after pulling an update', 14, "me.par.Autoupdate != 'off'"),
            # Development
            ('Headerdev', 'Development', None, False, 'header', None, 15, None),
            ('Devmode', 'Dev Mode', 'off', False, 'menu', 'Enable version bump prompts on project save', 16, None),
            ('Onlybumpdirty', 'Only Bump When Dirty', True, False, 'toggle', 'Skip version bump if component has no changes', 17, None),
            ('Forcebump', 'Force Version Bump', None, False, 'pulse', 'Manually trigger version bump dialog and save tox', 18, None),
        ]

        for name, label, default, read_only, param_type, help_text, order, enable_expr in params:
            # Skip if parameter already exists
            if hasattr(comp.par, name):
                continue

            # Create parameter based on type
            if param_type == 'header':
                new_par = version_page.appendHeader(name, label=label)
                new_par[0].startSection = True
            elif param_type == 'str':
                new_par = version_page.appendStr(name, label=label)
                new_par[0].default = default
                new_par[0].val = default
                new_par[0].readOnly = read_only
            elif param_type == 'file':
                new_par = version_page.appendFile(name, label=label)
                new_par[0].default = default
                new_par[0].val = default
            elif param_type == 'toggle':
                new_par = version_page.appendToggle(name, label=label)
                new_par[0].default = default
                new_par[0].val = default
            elif param_type == 'menu':
                new_par = version_page.appendMenu(name, label=label)
                if name == 'Devmode':
                    new_par[0].menuNames = ['off', 'auto', 'always']
                    new_par[0].menuLabels = ['Disabled', 'Auto (In Repo)', 'Always']
                else:
                    new_par[0].menuNames = ['off', 'prompt', 'always']
                    new_par[0].menuLabels = ['Disabled', 'Prompt to Update', 'Always Update']
                new_par[0].default = default
                new_par[0].val = default
            elif param_type == 'pulse':
                new_par = version_page.appendPulse(name, label=label)

            # Set order, help, and enable expression
            new_par[0].order = order
            if help_text:
                new_par[0].help = help_text
            if enable_expr:
                new_par[0].enableExpr = enable_expr

        # Set default Versionfile path if newly created (empty)
        if not comp.par.Versionfile.eval():
            default_path = os.path.join(project.folder, f"{comp.name.lower()}-version.json")
            comp.par.Versionfile.val = default_path
            comp.par.Versionfile.default = default_path

    # =========================================================================
    # PUBLIC PROPERTIES (Uppercase for TD promotion)
    # =========================================================================

    @property
    def Versionfile(self):
        """Get the full path to this component's version file"""
        path = str(self._versionOwnerComp.par.Versionfile.eval())
        if path:
            # Resolve relative paths against project.folder
            if not os.path.isabs(path):
                path = os.path.join(project.folder, path)
            return path
        return os.path.join(project.folder, f"{self._versionOwnerComp.name.lower()}-version.json")

    @property
    def VersionInfo(self):
        """Get current version info from parameters"""
        return {
            'version': str(self._versionOwnerComp.par.Version.eval()),
            'build': str(self._versionOwnerComp.par.Build.eval()),
            'td_version': str(self._versionOwnerComp.par.Tdversion.eval()),
            'td_build': str(self._versionOwnerComp.par.Tdbuild.eval()),
            'last_update': str(self._versionOwnerComp.par.Lastupdate.eval()),
            'version_url': str(self._versionOwnerComp.par.Versionurl.eval()),
        }

    @property
    def VersionString(self):
        """Get formatted version string (e.g., 'v1.0.0.123')"""
        info = self.VersionInfo
        return f"v{info['version']}.{info['build']}"

    @property
    def VersionUrl(self):
        """Get the URL to the remote version file"""
        return str(self._versionOwnerComp.par.Versionurl.eval())

    @property
    def VersionCheckEnabled(self):
        """Check if version checking is enabled"""
        return bool(self._versionOwnerComp.par.Versioncheckenabled.eval())

    @property
    def Devmode(self):
        """Get dev mode: 'off', 'auto', or 'always'"""
        return str(self._versionOwnerComp.par.Devmode.eval())

    @property
    def Token(self):
        """Get the GitHub token for authenticated requests"""
        return str(self._versionOwnerComp.par.Token.eval())

    @property
    def Usetoken(self):
        """Check if token authentication is enabled"""
        return bool(self._versionOwnerComp.par.Usetoken.eval())

    @property
    def Autoupdate(self):
        """Get auto update mode: 'off', 'prompt', or 'always'"""
        return str(self._versionOwnerComp.par.Autoupdate.eval())

    @property
    def Reloadonupdate(self):
        """Check if tox should be reloaded after an update"""
        return bool(self._versionOwnerComp.par.Reloadonupdate.eval())

    @property
    def Onlybumpdirty(self):
        """Check if version bump should only happen when component is dirty"""
        return bool(self._versionOwnerComp.par.Onlybumpdirty.eval())

    # =========================================================================
    # PUBLIC METHODS (Uppercase for TD promotion)
    # =========================================================================

    def _isDevActive(self):
        """Check if dev mode is currently active based on mode setting"""
        mode = self.Devmode
        if mode == 'off':
            return False
        if mode == 'auto':
            return self.IsInRepo
        if mode == 'always':
            return True
        return False

    def ReloadTox(self):
        """Override AcroToxExt.ReloadTox to refresh version params after reload."""
        result = super().ReloadTox()

        # Always refresh version params from disk after reload,
        # regardless of Reloadcustom setting
        if result:
            self._refreshVersionFromDisk()

        return result

    def _refreshVersionFromDisk(self):
        """Read version file from disk and update version params."""
        version_file = self.Versionfile
        if not version_file or not os.path.exists(version_file):
            return
        try:
            with open(version_file, 'r') as f:
                data = json.load(f)
            self.UpdateVersionParams(
                version=data.get('version'),
                build=data.get('build'),
                td_version=data.get('td_version'),
                td_build=data.get('td_build'),
            )
        except Exception as e:
            print(f"Error reading {version_file}: {e}")

    def GetRemoteVersion(self):
        """
        Fetch the latest version from remote repository.

        If Versionurl is set, fetches via HTTP.
        If Repopath is set (and Versionurl is empty), does git fetch and reads
        the version file from the remote tracking branch.
        """
        repo_url = self.VersionUrl
        repo_path = self.Repopath

        # Try HTTP URL first
        if repo_url:
            try:
                # Build request with optional token authentication
                req = urllib.request.Request(repo_url)
                if self.Usetoken and self.Token:
                    req.add_header('Authorization', f'token {self.Token}')

                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode())
                    return {
                        'version': data.get('version', '0.0.0'),
                        'build': str(data.get('build', 0)),
                        'td_version': data.get('td_version', ''),
                        'td_build': data.get('td_build', ''),
                    }
            except (urllib.error.URLError, json.JSONDecodeError, Exception) as e:
                print(f"Error fetching remote version via URL for {self._versionOwnerComp.path}: {e}")
                # Fall through to try local repo if available

        # Try local git repo
        if repo_path and os.path.exists(repo_path):
            try:
                # Fetch latest from remote
                fetch_result = subprocess.run(
                    ['git', 'fetch'],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                if fetch_result.returncode != 0:
                    print(f"Git fetch failed: {fetch_result.stderr}")
                    return None

                # Read version file from remote tracking branch (origin/HEAD or origin/main)
                # Git show needs a repo-relative path
                vf_abs = self.Versionfile
                if repo_path:
                    vf = os.path.relpath(vf_abs, repo_path).replace('\\', '/')
                else:
                    vf = os.path.basename(vf_abs)
                show_result = subprocess.run(
                    ['git', 'show', f'origin/HEAD:{vf}'],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                if show_result.returncode != 0:
                    # Try origin/main as fallback
                    show_result = subprocess.run(
                        ['git', 'show', f'origin/main:{vf}'],
                        cwd=repo_path,
                        capture_output=True,
                        text=True
                    )
                if show_result.returncode != 0:
                    # Try origin/master as fallback
                    show_result = subprocess.run(
                        ['git', 'show', f'origin/master:{vf}'],
                        cwd=repo_path,
                        capture_output=True,
                        text=True
                    )

                if show_result.returncode == 0:
                    data = json.loads(show_result.stdout)
                    return {
                        'version': data.get('version', '0.0.0'),
                        'build': str(data.get('build', 0)),
                        'td_version': data.get('td_version', ''),
                        'td_build': data.get('td_build', ''),
                    }
                else:
                    print(f"Could not read {vf} from remote branch: {show_result.stderr}")

            except (json.JSONDecodeError, Exception) as e:
                print(f"Error fetching remote version via git for {self._versionOwnerComp.path}: {e}")

        return None

    def CompareVersions(self, local_version, remote_version):
        """
        Compare two version strings.
        Returns: 1 if local > remote, -1 if local < remote, 0 if equal
        """
        def parse_version(v):
            parts = [int(x) for x in str(v).split('.')]
            while len(parts) < 3:
                parts.append(0)
            return parts

        local_parts = parse_version(local_version)
        remote_parts = parse_version(remote_version)

        for l, r in zip(local_parts, remote_parts):
            if l > r:
                return 1
            elif l < r:
                return -1
        return 0

    def HasUpdate(self):
        """
        Check if an update is available.
        Returns (has_update, remote_info) tuple.
        Skipped when dev mode is active or VersionCheckEnabled is off.
        """
        if self._isDevActive() or not self.VersionCheckEnabled:
            return False, None

        remote = self.GetRemoteVersion()
        if not remote:
            return False, None

        local = self.VersionInfo

        # Compare semantic version first
        version_cmp = self.CompareVersions(local['version'], remote['version'])
        if version_cmp < 0:
            return True, remote
        elif version_cmp == 0 and int(remote['build']) > int(local['build']):
            return True, remote

        return False, remote

    def CheckForUpdates(self):
        """
        Check for updates and log results to textport.
        Returns (has_update, remote_info) tuple.
        """
        if not self.VersionCheckEnabled:
            return False, None

        has_update, remote_info = self.HasUpdate()

        if has_update and remote_info:
            local = self.VersionInfo
            local_str = f"v{local['version']}.{local['build']}"
            remote_str = f"v{remote_info['version']}.{remote_info['build']}"
            print(f"{self._versionOwnerComp.path}: Update available {local_str} -> {remote_str}")

        elif remote_info:
            # Check if local is ahead of remote
            local = self.VersionInfo
            version_cmp = self.CompareVersions(local['version'], remote_info['version'])

            if version_cmp > 0 or (version_cmp == 0 and int(local['build']) > int(remote_info['build'])):
                local_str = f"v{local['version']}.{local['build']}"
                remote_str = f"v{remote_info['version']}.{remote_info['build']}"

                if self._isDevActive():
                    print(f"{self._versionOwnerComp.path}: Local ahead of remote ({local_str} > {remote_str})")
                else:
                    print(f"WARNING: {self._versionOwnerComp.path}: Local version ({local_str}) is ahead of remote ({remote_str})")

        return has_update, remote_info

    def UpdateVersionParams(self, version=None, build=None, td_version=None, td_build=None, last_update=None):
        """Update version parameters on the component (temporarily unlocks read-only params)"""
        import datetime

        comp = self._versionOwnerComp

        if version is not None:
            comp.par.Version.readOnly = False
            comp.par.Version.val = str(version)
            comp.par.Version.readOnly = True
        if build is not None:
            comp.par.Build.readOnly = False
            comp.par.Build.val = str(build)
            comp.par.Build.readOnly = True
        if td_version is not None:
            comp.par.Tdversion.readOnly = False
            comp.par.Tdversion.val = str(td_version)
            comp.par.Tdversion.readOnly = True
        if td_build is not None:
            comp.par.Tdbuild.readOnly = False
            comp.par.Tdbuild.val = str(td_build)
            comp.par.Tdbuild.readOnly = True
        if last_update is not None:
            comp.par.Lastupdate.readOnly = False
            comp.par.Lastupdate.val = str(last_update)
            comp.par.Lastupdate.readOnly = True
        elif any([version, build, td_version, td_build]):
            # Auto-update timestamp if any version info changed
            comp.par.Lastupdate.readOnly = False
            comp.par.Lastupdate.val = datetime.datetime.now().isoformat()
            comp.par.Lastupdate.readOnly = True

    def PerformUpdate(self, remote_version):
        """
        Perform auto-update. Respects Autoupdate mode (off/prompt/always).
        - If Repopath is set, runs git pull
        - If Externaltoxpath is set, reloads the tox

        Override this method in subclasses for custom update behavior.
        """
        if self._isDevActive():
            print(f"PerformUpdate: Skipped - dev mode is active for {self._versionOwnerComp.path}")
            return False

        if self.Autoupdate == 'off':
            print(f"PerformUpdate: Auto updates disabled for {self._versionOwnerComp.path}")
            return False

        # Prompt user if in prompt mode
        if self.Autoupdate == 'prompt':
            local = self.VersionInfo
            local_str = f"v{local['version']}.{local['build']}"
            remote_str = f"v{remote_version['version']}.{remote_version['build']}"
            result = ui.messageBox(
                'Update Available',
                f"Update {self._versionOwnerComp.path}?\n\n{local_str} → {remote_str}",
                buttons=['Update', 'Skip']
            )
            if result != 0:
                return False

        comp = self._versionOwnerComp
        repo_path = self.Repopath
        tox_path = self.Externaltoxpath

        # Git pull if repo path is configured
        if repo_path:
            if not os.path.exists(repo_path):
                print(f"PerformUpdate: Repo path does not exist: {repo_path}")
                return False

            try:
                result = subprocess.run(
                    ['git', 'pull'],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print(f"PerformUpdate: Git pull successful in {repo_path}")
                    print(result.stdout)
                else:
                    print(f"PerformUpdate: Git pull failed: {result.stderr}")
                    return False
            except Exception as e:
                print(f"PerformUpdate: Error running git pull: {e}")
                return False

        # Reload tox if enabled and external tox path is configured
        if self.Reloadonupdate and tox_path and os.path.exists(tox_path):
            try:
                comp.par.reinitnet.pulse()
                print(f"PerformUpdate: Reloaded {tox_path} for {comp.path}")
            except Exception as e:
                print(f"PerformUpdate: Error reloading tox: {e}")
                return False

        # Update version params from remote
        if remote_version:
            self.UpdateVersionParams(
                version=remote_version.get('version'),
                build=remote_version.get('build'),
                td_version=remote_version.get('td_version'),
                td_build=remote_version.get('td_build')
            )

        return True

    # =========================================================================
    # DEV MODE METHODS (Uppercase for TD promotion)
    # =========================================================================

    def GetBuildNumberFromProjectName(self):
        """Extract build number from project name (e.g., 'AcroTDCore.246.toe' -> 246)"""
        try:
            # project.name format: 'AcroTDCore.246.toe'
            parts = project.name.split('.')
            if len(parts) >= 2:
                return int(parts[-2])
        except (ValueError, IndexError):
            pass
        return int(self.VersionInfo['build'])

    def PromptVersionBump(self, force=False):
        """
        Prompt user to bump version when saving.

        Args:
            force: If True, bypass dev mode and dirty state checks
        """
        if not force:
            if not self._isDevActive():
                return

            # Skip if not dirty and Onlybumpdirty is enabled
            if self.Onlybumpdirty and not self.IsDirty:
                return

        local_version = self.VersionInfo
        new_build = self.GetBuildNumberFromProjectName()

        # Parse current version (fallback to 1.0.0 if empty)
        version_str = local_version['version'] or '1.0.0'
        parts = [int(x) for x in version_str.split('.') if x]
        while len(parts) < 3:
            parts.append(0)
        major, minor, patch = parts[0], parts[1], parts[2]

        is_semantic_bump = False
        should_save = False
        new_version = local_version['version']

        # Prompt for semantic bump if forced, dirty, or if Onlybumpdirty is disabled (scene-level tracking)
        if force or self.IsDirty or not self.Onlybumpdirty:
            comp_path = self._versionOwnerComp.path
            message = (f"{comp_path}\n\n"
                       f"Current version: v{local_version['version']}.{local_version['build']}\n"
                       f"New build: {new_build}\n\n"
                       f"Would you like to bump the semantic version?")
            title = 'Force Version Bump' if force else 'Version Update'
            result = ui.messageBox(title, message,
                                   buttons=['Major', 'Minor', 'Patch', 'Build', "Don't Save"])

            if result == 0:  # Major
                new_version = f"{major + 1}.0.0"
                is_semantic_bump = True
                should_save = True
            elif result == 1:  # Minor
                new_version = f"{major}.{minor + 1}.0"
                is_semantic_bump = True
                should_save = True
            elif result == 2:  # Patch
                new_version = f"{major}.{minor}.{patch + 1}"
                is_semantic_bump = True
                should_save = True
            elif result == 3:  # Build - save with build bump only, no semantic version change
                should_save = True
            elif result == 4:  # Don't Save - skip everything
                print(f"{self.ownerComp.name} - Skipped (no changes saved)")
                return

        if should_save:
            # Update version file + params (build, td_version, etc.)
            self.UpdateVersionFile(new_version, new_build)
            self.UpdateVersionParams(
                version=new_version,
                build=new_build,
                td_version=project.saveVersion,
                td_build=project.saveBuild
            )

            if is_semantic_bump:
                self.UpdateChangelog(new_version)

            print(f"{self.ownerComp.name} - Version updated to v{new_version}.{new_build}")

            # Auto-save tox to capture the version bump
            self.SaveTox(prompt=False)

    def UpdateVersionFile(self, new_version, new_build):
        """Update the version file with new version info"""
        version_file = self.Versionfile

        try:
            # Read existing data or create new
            if os.path.exists(version_file):
                with open(version_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {}

            # Update version info
            data['version'] = new_version
            data['build'] = new_build
            data['last_update'] = datetime.datetime.now().isoformat()
            data['td_version'] = project.saveVersion
            data['td_build'] = project.saveBuild

            # Write back
            with open(version_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"Error updating version file: {e}")

    def UpdateChangelog(self, new_version):
        """Add new version entry to component-specific CHANGELOG and open in editor"""
        # Use Repopath if set, otherwise fall back to project.folder
        base_path = self.Repopath if self.Repopath else project.folder
        changelog_name = f"{self._versionOwnerComp.name.lower()}-CHANGELOG.md"
        changelog_path = os.path.join(base_path, changelog_name)
        today = datetime.datetime.now().strftime('%Y-%m-%d')

        new_entry = f"\n## [{new_version}] - {today}\n- \n"

        try:
            if os.path.exists(changelog_path):
                with open(changelog_path, 'r') as f:
                    content = f.read()

                # Insert new entry after the header
                header_end = content.find('\n\n## ')
                if header_end == -1:
                    # No existing entries, append after header
                    content = content.rstrip() + '\n' + new_entry
                else:
                    # Insert before first version entry
                    content = content[:header_end] + '\n' + new_entry + content[header_end+1:]
            else:
                # Create new changelog
                content = f"# Changelog\n\nAll notable changes to this project will be documented in this file.{new_entry}"

            with open(changelog_path, 'w') as f:
                f.write(content)

            # Open in default editor
            if app.osName == 'Windows':
                os.startfile(changelog_path)
            else:
                subprocess.run(['open', changelog_path])

            print(f"{changelog_name} updated for version {new_version}")

        except Exception as e:
            print(f"Error updating changelog: {e}")

    # =========================================================================
    # PULSE HANDLERS
    # =========================================================================

    def pulse_Forcebump(self):
        """Force a version bump, bypassing dev mode and dirty checks"""
        self.PromptVersionBump(force=True)
