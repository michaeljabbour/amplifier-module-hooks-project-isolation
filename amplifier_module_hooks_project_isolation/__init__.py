"""
amplifier-module-hooks-project-isolation

Per-project session storage for Amplifier CLI applications.
Automatically isolates sessions by project (git root or CWD).
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Optional

from amplifier_core.models import HookResult

__version__ = "1.0.0"
__amplifier_module_type__ = "hook"


async def mount(coordinator, config: dict):
    """
    Mount function that registers the project isolation hook.

    Args:
        coordinator: Amplifier ModuleCoordinator instance
        config: Configuration dictionary with keys:
            - use_git_root: bool (default: True)
            - storage_base: str (default: ~/.amplifier/projects)
            - create_dirs: bool (default: True)
    """
    # Extract configuration
    use_git_root = config.get("use_git_root", True)
    storage_base = Path(config.get("storage_base", "~/.amplifier/projects")).expanduser()
    create_dirs = config.get("create_dirs", True)

    # Create handler
    handler = _ProjectIsolationHandler(
        use_git_root=use_git_root,
        storage_base=storage_base,
        create_dirs=create_dirs
    )

    # Register hook for session start
    coordinator.hooks.register("session:start", handler.on_session_start)


class _ProjectIsolationHandler:
    """Internal handler for project isolation logic."""

    def __init__(self, use_git_root: bool, storage_base: Path, create_dirs: bool):
        """
        Initialize the project isolation handler.

        Args:
            use_git_root: Whether to use git root for project detection
            storage_base: Base directory for project storage
            create_dirs: Whether to auto-create directories
        """
        self.use_git_root = use_git_root
        self.storage_base = storage_base
        self.create_dirs = create_dirs

    async def on_session_start(self, event: str, context: dict) -> HookResult:
        """
        Hook handler called when a session starts.

        Detects the current project and sets the storage path accordingly.
        Modifies context in place and returns HookResult.

        Args:
            event: Event name (always "session:start")
            context: Session context dictionary (modified in place)

        Returns:
            HookResult with action="continue"
        """
        # Detect project root
        project_root = self._detect_project_root()

        # Generate project slug
        project_slug = self._generate_slug(project_root.name)

        # Build storage path
        storage_path = self.storage_base / project_slug / "sessions"

        # Create directories if configured
        if self.create_dirs:
            storage_path.mkdir(parents=True, exist_ok=True)

        # Set storage path in context (modified in place)
        context["storage_path"] = str(storage_path)
        context["project_root"] = str(project_root)
        context["project_slug"] = project_slug

        # Return success
        return HookResult(action="continue")

    def _detect_project_root(self) -> Path:
        """
        Detect the project root directory.

        Returns:
            Path to project root (git root or CWD)
        """
        if self.use_git_root:
            git_root = self._get_git_root()
            if git_root:
                return git_root

        # Fallback to current working directory
        return Path.cwd()

    def _get_git_root(self) -> Optional[Path]:
        """
        Get the git repository root path.

        Returns:
            Path to git root, or None if not in a git repository
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True,
                timeout=2,
                cwd=os.getcwd()
            )
            return Path(result.stdout.strip())
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def _generate_slug(self, name: str) -> str:
        """
        Generate a URL-safe slug from a project name.

        Args:
            name: Project directory name

        Returns:
            URL-safe slug (lowercase, alphanumeric + hyphens)
        """
        # Convert to lowercase
        slug = name.lower()

        # Replace spaces and underscores with hyphens
        slug = re.sub(r'[\s_]+', '-', slug)

        # Remove all non-alphanumeric characters except hyphens
        slug = re.sub(r'[^a-z0-9-]', '', slug)

        # Remove duplicate hyphens
        slug = re.sub(r'-+', '-', slug)

        # Strip leading/trailing hyphens
        slug = slug.strip('-')

        # Ensure non-empty
        if not slug:
            slug = "default"

        return slug
