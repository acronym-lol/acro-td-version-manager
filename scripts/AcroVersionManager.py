"""
AcroVersionManager - Central manager for version tracking across all components.

Discovers components with 'version_tracking' tag and checks them for updates.
Provides reporting, popup notifications, and update management.
"""
import traceback

from CallbacksExt import CallbacksExt
from TDStoreTools import StorageManager
from AcroVersionExt import AcroVersionExt, VERSION_TAG
from AcroToxExt import TOX_TAG


class AcroVersionManager(CallbacksExt, AcroVersionExt):
    """
    Central version manager that discovers and checks all versioned components.
    """

    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        # init callbacks
        self.callbackDat = self.ownerComp.par.Callbackdat.eval()
        try:
            CallbacksExt.__init__(self, ownerComp)
        except:
            self.ownerComp.addScriptError(traceback.format_exc() + \
                    "Error in CallbacksExt __init__. See textport.")
            print()
            print("Error initializing callbacks - " + self.ownerComp.path)
            print(traceback.format_exc())
        # run onInit callback
        try:
            self.DoCallback('onInit', {'ownerComp':self.ownerComp})
        except:
            self.ownerComp.addScriptError(traceback.format_exc() + \
                    "Error in custom onInit callback. See textport.")
            print(traceback.format_exc())
        # stored items for tracking ignored/skipped
        storedItems = [
            {'name': 'SkippedVersions', 'default': {}, 'readOnly': False,
                'property': True, 'dependable': True},
            {'name': 'IgnoredComponents', 'default': [], 'readOnly': False,
                'property': True, 'dependable': True},
        ]
        self.stored = StorageManager(self, ownerComp, storedItems)

        # Initialize version tracking
        AcroVersionExt.__init__(self, ownerComp)

    # -------------------------------------------------------------------------
    # Core Methods
    # -------------------------------------------------------------------------

    def CheckAll(self):
        """Check all versioned components for updates. Called on startup or manually."""
        updates = self._scanForUpdates()
        version_str = self.VersionString
        print("\n" + "=" * 60)
        print(f"AcroVersionManager - {version_str}")

        print(f"Checked {len(self._getVersionedComponents())} versioned component(s).")
        if not updates:
            if self.ownerComp.par.Printtotextport.eval():
                print("Status: All components are up to date.")
                self.PrintReport()
            return []
        
        print("=" * 60)

        # Print report if enabled
        if self.ownerComp.par.Printtotextport.eval():
            self._printReport(updates)

        # Show popup if enabled
        if self.ownerComp.par.Showpopup.eval():
            self._showUpdateDialog(updates)

        return updates

    def PrintReport(self):
        """Print version status report for all versioned components."""
        components = self._getVersionedComponents()

        print("\n" + "=" * 60)
        print("VERSION STATUS REPORT")
        print("=" * 60)

        for comp in components:
            info = comp.VersionInfo
            has_update, remote = comp.HasUpdate()

            # Determine status
            if comp.path in self.stored['IgnoredComponents']:
                status = "IGNORED"
            elif has_update and remote:
                remote_ver = f"{remote['version']}.{remote['build']}"
                status = f"UPDATE AVAILABLE -> v{remote_ver}"
            else:
                status = "OK"

            print(f"\n{comp.path}")
            print(f"  Version: v{info['version']}.{info['build']}")
            if remote:
                print(f"   Remote: v{remote['version']}.{remote['build']}")
            print(f"   Status: {status}")

        print("\n" + "=" * 60)

    def ClearIgnored(self):
        """Clear all ignored components and skipped versions."""
        self.stored['SkippedVersions'] = {}
        self.stored['IgnoredComponents'] = []
        print("VersionManager: Cleared all ignored components and skipped versions.")

    # -------------------------------------------------------------------------
    # Skip/Ignore Management
    # -------------------------------------------------------------------------

    def SkipVersion(self, comp, version):
        """Mark a version as skipped for a component."""
        skipped = self.stored['SkippedVersions']
        skipped[comp.path] = version
        self.stored['SkippedVersions'] = skipped
        print(f"VersionManager: Skipping version {version} for {comp.path}")

    def IgnoreComponent(self, comp):
        """Ignore future updates for a component."""
        ignored = self.stored['IgnoredComponents']
        if comp.path not in ignored:
            ignored.append(comp.path)
            self.stored['IgnoredComponents'] = ignored
        print(f"VersionManager: Ignoring updates for {comp.path}")

    def UnignoreComponent(self, comp):
        """Stop ignoring a component."""
        ignored = self.stored['IgnoredComponents']
        if comp.path in ignored:
            ignored.remove(comp.path)
            self.stored['IgnoredComponents'] = ignored
        print(f"VersionManager: Re-enabled updates for {comp.path}")

    # -------------------------------------------------------------------------
    # Update Management
    # -------------------------------------------------------------------------

    def UpdateComponent(self, comp, remote_version):
        """
        Trigger update for a component if it supports performUpdate().
        Returns True if update was performed, False otherwise.
        """
        if not self.ownerComp.par.Automaticupdates.eval():
            print(f"VersionManager: Auto-update disabled. Cannot update {comp.path}")
            return False

        if not hasattr(comp, 'PerformUpdate'):
            print(f"VersionManager: {comp.path} does not support auto-update")
            return False

        try:
            comp.PerformUpdate(remote_version)
            print(f"VersionManager: Updated {comp.path} to v{remote_version['version']}.{remote_version['build']}")
            return True
        except Exception as e:
            print(f"VersionManager: Failed to update {comp.path}: {e}")
            return False

    def UpdateAll(self, updates):
        """Update all components that support auto-update."""
        if not self.ownerComp.par.Automaticupdates.eval():
            print("VersionManager: Auto-update disabled.")
            return

        updated = 0
        for update_info in updates:
            comp = update_info['component']
            remote = update_info['remote']
            if hasattr(comp, 'PerformUpdate'):
                if self.UpdateComponent(comp, remote):
                    updated += 1

        print(f"VersionManager: Updated {updated} component(s)")

    # -------------------------------------------------------------------------
    # Internal Methods
    # -------------------------------------------------------------------------

    def _getVersionedComponents(self):
        """Find all components with version_tracking tag."""
        return root.findChildren(tags=[VERSION_TAG])

    def _getToxComponents(self):
        """Find all components with tox_managed tag (includes version-tracked components)."""
        return root.findChildren(tags=[TOX_TAG])

    def _scanForUpdates(self):
        """Scan all versioned components and return list of those with updates."""
        components = self._getVersionedComponents()
        updates = []
        skipped = self.stored['SkippedVersions']
        ignored = self.stored['IgnoredComponents']

        for comp in components:
            # Skip self to avoid interrupting our own operation
            if comp == self.ownerComp:
                continue

            # Skip ignored components
            if comp.path in ignored:
                continue

            # Skip if component has checking disabled
            if hasattr(comp, 'VersionCheckEnabled') and not comp.VersionCheckEnabled:
                continue

            # Check for update
            try:
                has_update, remote = comp.HasUpdate()
            except Exception as e:
                print(f"VersionManager: Error checking {comp.path}: {e}")
                continue

            if not has_update or not remote:
                continue

            # Check if this version was skipped
            remote_ver = f"{remote['version']}.{remote['build']}"
            if skipped.get(comp.path) == remote_ver:
                continue

            updates.append({
                'component': comp,
                'local': comp.VersionInfo,
                'remote': remote,
                'supports_update': hasattr(comp, 'PerformUpdate')
            })

        return updates

    def _printReport(self, updates):
        """Print update report to textport."""
        print("\n" + "=" * 60)
        print(f"VERSION UPDATES AVAILABLE ({len(updates)} component(s))")
        print("=" * 60)

        for update in updates:
            comp = update['component']
            local = update['local']
            remote = update['remote']
            local_ver = f"v{local['version']}.{local['build']}"
            remote_ver = f"v{remote['version']}.{remote['build']}"
            auto = "[auto-update]" if update['supports_update'] else ""

            print(f"\n{comp.path} {auto}")
            print(f"  Current: {local_ver}")
            print(f"  Available: {remote_ver}")

        print("\n" + "=" * 60)

    def _showUpdateDialog(self, updates):
        """Show popup dialog with update options."""
        if not updates:
            return

        # Build message
        lines = [f"Updates available for {len(updates)} component(s):\n"]
        for update in updates:
            comp = update['component']
            local = update['local']
            remote = update['remote']
            local_ver = f"v{local['version']}.{local['build']}"
            remote_ver = f"v{remote['version']}.{remote['build']}"
            lines.append(f"• {comp.name}: {local_ver} → {remote_ver}")

        message = "\n".join(lines)

        # Show dialog with options
        # For now, simple acknowledgment - could be expanded to full UI later
        result = ui.messageBox('Updates Available', message,
                               buttons=['Dismiss', 'Skip All', 'Ignore All'])

        if result == 1:  # Skip All
            for update in updates:
                remote = update['remote']
                remote_ver = f"{remote['version']}.{remote['build']}"
                self.SkipVersion(update['component'], remote_ver)
        elif result == 2:  # Ignore All
            for update in updates:
                self.IgnoreComponent(update['component'])

    def onStart(self):
        """Called on project start to check for updates."""
        if self.ownerComp.par.Checkonstart.eval():
            startup_delay = self.ownerComp.par.Startupdelay.eval()
            run(self.CheckAll, delayFrames=startup_delay)

    def onSaveStart(self):
        """Called before project saves - handle version bumps and dirty tox files."""
        # Handle version-tracked components (version bump + auto tox save)
        self.PromptVersionBumpAll()

        # Handle tox-only components that use Onsave parameter
        if hasattr(self.ownerComp.par, 'Checkdirtyonsave') and self.ownerComp.par.Checkdirtyonsave.eval():
            self.PromptSaveDirtyComponents()

    # -------------------------------------------------------------------------
    # Version Bump Management
    # -------------------------------------------------------------------------

    def PromptVersionBumpAll(self):
        """Call PromptVersionBump on all version-tracked components with dev mode active."""
        for comp in self._getVersionedComponents():
            # Skip self to avoid interrupting save operation
            if comp == self.ownerComp:
                continue

            if not hasattr(comp, 'PromptVersionBump'):
                continue

            # Check dev mode using public properties (can't use private _isDevActive)
            if not hasattr(comp, 'Devmode'):
                continue

            devmode = comp.Devmode
            is_dev_active = False
            if devmode == 'always':
                is_dev_active = True
            elif devmode == 'auto':
                is_dev_active = hasattr(comp, 'IsInRepo') and comp.IsInRepo
            # devmode == 'off' stays False

            if is_dev_active:
                comp.PromptVersionBump()

    # -------------------------------------------------------------------------
    # Dirty Tox Management
    # -------------------------------------------------------------------------

    def GetDirtyComponents(self):
        """Find all dirty tox-managed components with save-on-save enabled."""
        dirty = []
        for comp in self._getToxComponents():
            if hasattr(comp, 'Onsave') and comp.Onsave != 'off':
                if hasattr(comp, 'IsDirty') and comp.IsDirty:
                    dirty.append(comp)
        return dirty

    def PromptSaveDirtyComponents(self):
        """
        Find all dirty tox-managed components and save based on their Onsave mode.
        Call this from project callbacks onSaveStart.
        """
        dirty_comps = self.GetDirtyComponents()

        if not dirty_comps:
            return

        for comp in dirty_comps:
            comp.PromptSaveTox()

    # -------------------------------------------------------------------------
    # Pulse Handlers
    # -------------------------------------------------------------------------

    def pulse_Checkall(self):
        """Pulse handler for Check All button."""
        self.CheckAll()

    def pulse_Printreport(self):
        """Pulse handler for Print Report button."""
        self.PrintReport()

    def pulse_Clearignored(self):
        """Pulse handler for Clear Ignored button."""
        self.ClearIgnored()
