"""
Behavioral tests for project isolation module.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, Mock
from amplifier_module_hooks_project_isolation import _ProjectIsolationHandler


class TestSlugGeneration:
    """Test slug generation from project names."""

    def test_simple_name(self):
        """Test slug generation for simple names."""
        handler = _ProjectIsolationHandler(True, Path("/tmp"), True)
        assert handler._generate_slug("project") == "project"

    def test_spaces_to_hyphens(self):
        """Test that spaces are converted to hyphens."""
        handler = _ProjectIsolationHandler(True, Path("/tmp"), True)
        assert handler._generate_slug("my project") == "my-project"

    def test_underscores_to_hyphens(self):
        """Test that underscores are converted to hyphens."""
        handler = _ProjectIsolationHandler(True, Path("/tmp"), True)
        assert handler._generate_slug("my_project") == "my-project"

    def test_special_characters_removed(self):
        """Test that special characters are removed."""
        handler = _ProjectIsolationHandler(True, Path("/tmp"), True)
        assert handler._generate_slug("project@v2!") == "projectv2"

    def test_uppercase_to_lowercase(self):
        """Test that uppercase is converted to lowercase."""
        handler = _ProjectIsolationHandler(True, Path("/tmp"), True)
        assert handler._generate_slug("MyProject") == "myproject"

    def test_duplicate_hyphens_removed(self):
        """Test that duplicate hyphens are removed."""
        handler = _ProjectIsolationHandler(True, Path("/tmp"), True)
        assert handler._generate_slug("my--project") == "my-project"

    def test_leading_trailing_hyphens_removed(self):
        """Test that leading/trailing hyphens are removed."""
        handler = _ProjectIsolationHandler(True, Path("/tmp"), True)
        assert handler._generate_slug("-project-") == "project"

    def test_empty_name_fallback(self):
        """Test that empty names fall back to 'default'."""
        handler = _ProjectIsolationHandler(True, Path("/tmp"), True)
        assert handler._generate_slug("") == "default"
        assert handler._generate_slug("!!!") == "default"


class TestProjectDetection:
    """Test project root detection."""

    def test_git_root_detection_success(self):
        """Test successful git root detection."""
        handler = _ProjectIsolationHandler(True, Path("/tmp"), True)

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(stdout="/repo/root\n", returncode=0)
            result = handler._get_git_root()
            assert result == Path("/repo/root")

    def test_git_root_detection_not_a_repo(self):
        """Test git root detection when not in a repo."""
        import subprocess
        handler = _ProjectIsolationHandler(True, Path("/tmp"), True)

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(128, 'git')
            result = handler._get_git_root()
            assert result is None

    def test_git_root_detection_timeout(self):
        """Test git root detection with timeout."""
        import subprocess
        handler = _ProjectIsolationHandler(True, Path("/tmp"), True)

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired('git', 2)
            result = handler._get_git_root()
            assert result is None

    def test_detect_project_root_git_enabled(self):
        """Test project detection with git enabled."""
        handler = _ProjectIsolationHandler(True, Path("/tmp"), True)

        with patch.object(handler, '_get_git_root') as mock_git:
            mock_git.return_value = Path("/repo/root")
            result = handler._detect_project_root()
            assert result == Path("/repo/root")

    def test_detect_project_root_git_fallback_to_cwd(self):
        """Test project detection falls back to CWD when git fails."""
        handler = _ProjectIsolationHandler(True, Path("/tmp"), True)

        with patch.object(handler, '_get_git_root') as mock_git, \
             patch('pathlib.Path.cwd') as mock_cwd:
            mock_git.return_value = None
            mock_cwd.return_value = Path("/current/dir")
            result = handler._detect_project_root()
            assert result == Path("/current/dir")

    def test_detect_project_root_git_disabled(self):
        """Test project detection with git disabled."""
        handler = _ProjectIsolationHandler(False, Path("/tmp"), True)

        with patch('pathlib.Path.cwd') as mock_cwd:
            mock_cwd.return_value = Path("/current/dir")
            result = handler._detect_project_root()
            assert result == Path("/current/dir")


class TestSessionHandler:
    """Test session start handler."""

    @pytest.mark.asyncio
    async def test_on_session_start_sets_context(self, tmp_path, session_context):
        """Test that on_session_start sets storage context."""
        storage_base = tmp_path / "storage"
        handler = _ProjectIsolationHandler(False, storage_base, True)

        with patch('pathlib.Path.cwd') as mock_cwd:
            mock_cwd.return_value = Path("/test/project")

            await handler.on_session_start("session:start", session_context)

            assert "storage_path" in session_context
            assert "project_root" in session_context
            assert "project_slug" in session_context
            assert session_context["project_slug"] == "project"

    @pytest.mark.asyncio
    async def test_on_session_start_creates_directories(self, tmp_path, session_context):
        """Test that directories are created when configured."""
        storage_base = tmp_path / "storage"
        handler = _ProjectIsolationHandler(False, storage_base, True)

        with patch('pathlib.Path.cwd') as mock_cwd:
            mock_cwd.return_value = Path("/test/project")

            await handler.on_session_start("session:start", session_context)

            expected_path = storage_base / "project" / "sessions"
            assert expected_path.exists()

    @pytest.mark.asyncio
    async def test_on_session_start_no_create_directories(self, tmp_path, session_context):
        """Test that directories are not created when disabled."""
        storage_base = tmp_path / "storage"
        handler = _ProjectIsolationHandler(False, storage_base, False)

        with patch('pathlib.Path.cwd') as mock_cwd:
            mock_cwd.return_value = Path("/test/project")

            await handler.on_session_start("session:start", session_context)

            expected_path = storage_base / "project" / "sessions"
            assert not expected_path.exists()

    @pytest.mark.asyncio
    async def test_on_session_start_with_git_root(self, tmp_path, session_context):
        """Test session start with git root detection."""
        storage_base = tmp_path / "storage"
        handler = _ProjectIsolationHandler(True, storage_base, True)

        with patch.object(handler, '_get_git_root') as mock_git:
            mock_git.return_value = Path("/repo/my-app")

            await handler.on_session_start("session:start", session_context)

            assert session_context["project_slug"] == "my-app"
            assert session_context["project_root"] == "/repo/my-app"
