"""
AcroToxExt - Mixin class for external tox file management in TouchDesigner components.

Usage:
    class MyComponent(AcroToxExt):
        def __init__(self, ownerComp):
            self.ownerComp = ownerComp
            AcroToxExt.__init__(self, ownerComp)

The mixin will automatically create a "Component" parameter page with:
    - Repopath: Repository folder (used by auto repo detection for save/dev modes)

    [External Tox]
    - Enableexternaltox: Enable external tox (syncs with TD built-in)
    - Externaltoxpath: Path to external tox file
    - Onsave: Save behavior on project save (Disabled / Prompt / Always / Auto)

    [Reload]
    - Reloadtox: Pulse to reload tox from disk
    - Reloadcustom: Reload custom parameters when reloading
    - Reloadbuiltin: Reload built-in parameters when reloading
"""

import os


# Tag used to identify tox-managed components
TOX_TAG = 'tox_managed'


class AcroToxExt:
    """
    Mixin class for external tox file management.
    Add this to any extension that needs tox save/reload functionality.
    """

    def __init__(self, ownerComp):
        self._toxOwnerComp = ownerComp

        # Ensure Component parameter page exists with all params
        self._ensureComponentPage()

        # Add tag so managers can discover this component
        self._ensureToxTag()

    def _ensureToxTag(self):
        """Ensure the component has the tox managed tag"""
        if TOX_TAG not in self._toxOwnerComp.tags:
            self._toxOwnerComp.tags.add(TOX_TAG)

    def _ensureComponentPage(self):
        """Create Component parameter page if it doesn't exist"""
        comp = self._toxOwnerComp

        # Check if Component page already exists
        comp_page = None
        for page in comp.customPages:
            if page.name == 'Component':
                comp_page = page
                break

        # Create page if it doesn't exist
        if comp_page is None:
            comp_page = comp.appendCustomPage('Component')

        # Define parameters to create
        # Format: (name, label, default, param_type, help_text, order, enable_expr, section)
        params = [
            # Repository (ungated - used by both tox and version systems)
            ('Repopath', 'Repository Folder', '', 'folder', 'Git repo folder for this component (used by auto save/dev modes)', 0, None, False),
            # External Tox
            ('Enableexternaltox', 'Enable External Tox', False, 'toggle', 'Enable external tox loading (syncs with TD built-in)', 1, None, True),
            ('Externaltoxpath', 'External Tox Path', '', 'file', 'Path to external tox file (syncs with TD built-in)', 2, 'me.par.Enableexternaltox', False),
            ('Onsave', 'Save on Project Save', 'off', 'menu', 'How to handle tox saving when the project saves', 3, 'me.par.Enableexternaltox', False),
            # Reload
            ('Reloadtox', 'Reload Tox', None, 'pulse', 'Reload the external tox file from disk', 4, 'me.par.Enableexternaltox', True),
            ('Reloadcustom', 'Reload Custom Parameters', True, 'toggle', 'Reload custom parameters when reloading tox', 5, 'me.par.Enableexternaltox', False),
            ('Reloadbuiltin', 'Reload Built-In Parameters', True, 'toggle', 'Reload built-in parameters when reloading tox', 6, 'me.par.Enableexternaltox', False),
        ]

        for name, label, default, param_type, help_text, order, enable_expr, section in params:
            # Skip if parameter already exists
            if hasattr(comp.par, name):
                continue

            # Create parameter based on type
            if param_type == 'toggle':
                new_par = comp_page.appendToggle(name, label=label)
                new_par[0].default = default
                new_par[0].val = default
            elif param_type == 'file':
                new_par = comp_page.appendFile(name, label=label)
                new_par[0].default = default
                new_par[0].val = default
            elif param_type == 'folder':
                new_par = comp_page.appendFolder(name, label=label)
                new_par[0].default = default
                new_par[0].val = default
            elif param_type == 'menu':
                new_par = comp_page.appendMenu(name, label=label)
                new_par[0].menuNames = ['off', 'prompt', 'always', 'auto']
                new_par[0].menuLabels = ['Disabled', 'Prompt to Save', 'Always Save', 'Auto (In Repo)']
                new_par[0].default = default
                new_par[0].val = default
            elif param_type == 'pulse':
                new_par = comp_page.appendPulse(name, label=label)

            # Set order, help, enable expression, and section break
            new_par[0].order = order
            if help_text:
                new_par[0].help = help_text
            if enable_expr:
                new_par[0].enableExpr = enable_expr
            if section:
                new_par[0].startSection = True

        # Bind TD's built-in external tox parameters to our custom parameters
        self._bindExternalToxParams()

    def _bindExternalToxParams(self):
        """Bind TD's externaltox and enableexternaltox to our managed parameters"""
        comp = self._toxOwnerComp

        # Only bind if our parameters exist
        if not hasattr(comp.par, 'Externaltoxpath') or not hasattr(comp.par, 'Enableexternaltox'):
            return

        # Bind TD's externaltox to our Externaltoxpath
        if comp.par.externaltox.mode != ParMode.EXPRESSION:
            comp.par.externaltox.expr = "me.par.Externaltoxpath"
            comp.par.externaltox.mode = ParMode.EXPRESSION

        # Bind TD's enableexternaltox to our Enableexternaltox
        if comp.par.enableexternaltox.mode != ParMode.EXPRESSION:
            comp.par.enableexternaltox.expr = "me.par.Enableexternaltox"
            comp.par.enableexternaltox.mode = ParMode.EXPRESSION

    # =========================================================================
    # PUBLIC PROPERTIES (Uppercase for TD promotion)
    # =========================================================================

    @property
    def IsDirty(self):
        """Check if component has unsaved changes"""
        return self._toxOwnerComp.dirty

    @property
    def Enableexternaltox(self):
        """Check if external tox loading is enabled"""
        return bool(self._toxOwnerComp.par.Enableexternaltox.eval())

    @property
    def Externaltoxpath(self):
        """Get our managed external tox path"""
        return str(self._toxOwnerComp.par.Externaltoxpath.eval())

    @property
    def Onsave(self):
        """Get save-on-project-save mode: 'off', 'prompt', 'always', or 'auto'"""
        return str(self._toxOwnerComp.par.Onsave.eval())

    @property
    def Repopath(self):
        """Get the repository folder path for auto repo detection"""
        return str(self._toxOwnerComp.par.Repopath.eval())

    @property
    def IsInRepo(self):
        """Check if the current project is in this component's repo"""
        repo = self.Repopath
        if not repo:
            return False
        proj = os.path.normpath(project.folder)
        repo = os.path.normpath(repo)
        # Match if project folder equals repo path (normal case)
        # or repo path is inside project folder (subtree case)
        return proj == repo or repo.startswith(proj + os.sep)

    @property
    def Reloadcustom(self):
        """Check if custom parameters should be reloaded"""
        return bool(self._toxOwnerComp.par.Reloadcustom.eval())

    @property
    def Reloadbuiltin(self):
        """Check if built-in parameters should be reloaded"""
        return bool(self._toxOwnerComp.par.Reloadbuiltin.eval())

    # =========================================================================
    # PUBLIC METHODS (Uppercase for TD promotion)
    # =========================================================================

    def GetToxSavePath(self):
        """
        Get the path where this component's tox should be saved.
        Uses Externaltoxpath if set, otherwise defaults to tox/[name].tox
        """
        if self.Externaltoxpath:
            return self.Externaltoxpath

        return os.path.join(project.folder, 'tox', f"{self._toxOwnerComp.name}.tox")

    def ReloadTox(self):
        """Reload the external tox file from disk"""
        comp = self._toxOwnerComp
        tox_path = self.Externaltoxpath

        if not tox_path or not os.path.exists(tox_path):
            print(f"ReloadTox: No tox file found for {comp.path}")
            return False

        try:
            comp.par.reinitnet.pulse(
                loadCustom=self.Reloadcustom,
                loadBuiltIn=self.Reloadbuiltin
            )
            print(f"ReloadTox: Reloaded {comp.path} from {tox_path}")
            return True
        except Exception as e:
            print(f"ReloadTox: Error reloading {comp.path}: {e}")
            return False

    def SaveTox(self, path=None, prompt=True):
        """
        Save component as tox file.

        Args:
            path: Override save path (uses GetToxSavePath() if None)
            prompt: Show confirmation dialog

        Returns:
            True if saved, False if cancelled or failed
        """
        save_path = path or self.GetToxSavePath()
        if not save_path:
            print(f"SaveTox: No save path for {self._toxOwnerComp.path}")
            return False

        if prompt:
            exists = os.path.exists(save_path)
            action = "Overwrite" if exists else "Create"
            result = ui.messageBox(
                'Save Tox',
                f'{action} external tox?\n{save_path}',
                buttons=['Save', 'Skip']
            )
            if result != 0:
                return False

        try:
            self._toxOwnerComp.save(save_path)
            # Update our path parameter if not already set
            if not self.Externaltoxpath:
                self._toxOwnerComp.par.Externaltoxpath = save_path
            # Enable external tox loading
            if not self.Enableexternaltox:
                self._toxOwnerComp.par.Enableexternaltox = True
            print(f"SaveTox: Saved {self._toxOwnerComp.path} to {save_path}")
            return True
        except Exception as e:
            print(f"SaveTox: Error saving {self._toxOwnerComp.path}: {e}")
            return False

    def PromptSaveTox(self):
        """Handle tox saving based on Onsave mode. Called on project save."""
        if self.Onsave == 'off':
            return False
        if not self.IsDirty:
            return False
        if self.Onsave == 'auto':
            if not self.IsInRepo:
                return False
            return self.SaveTox(prompt=False)
        if self.Onsave == 'always':
            return self.SaveTox(prompt=False)
        if self.Onsave == 'prompt':
            return self.SaveTox(prompt=True)
        return False

    # =========================================================================
    # PULSE HANDLERS
    # =========================================================================

    def pulse_Reloadtox(self):
        """Pulse handler for Reload Tox button"""
        self.ReloadTox()
