"""
Behavioral tests for project isolation module.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, Mock
from amplifier_core.models import HookResult
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

            result = await handler.on_session_start("session:start", session_context)

            assert isinstance(result, HookResult)
            assert result.action == "continue"
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

            # Should create directory with pattern: project-<hash>/sessions
            project_dirs = list(storage_base.glob("project-*"))
            assert len(project_dirs) == 1

            expected_path = project_dirs[0] / "sessions"
            assert expected_path.exists()

    @pytest.mark.asyncio
    async def test_on_session_start_no_create_directories(self, tmp_path, session_context):
        """Test that directories are not created when disabled."""
        storage_base = tmp_path / "storage"
        handler = _ProjectIsolationHandler(False, storage_base, False)

        with patch('pathlib.Path.cwd') as mock_cwd:
            mock_cwd.return_value = Path("/test/project")

            await handler.on_session_start("session:start", session_context)

            # No directories should be created
            assert not storage_base.exists()

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


class TestCollisionProofNaming:
    """Test collision-proof directory naming."""

    def test_generate_path_hash(self):
        """Test that path hash is generated correctly."""
        handler = _ProjectIsolationHandler(True, Path("/tmp"), True)

        # Same path should always generate same hash
        hash1 = handler._generate_path_hash("/test/project")
        hash2 = handler._generate_path_hash("/test/project")
        assert hash1 == hash2

        # Different paths should generate different hashes
        hash3 = handler._generate_path_hash("/different/project")
        assert hash1 != hash3

        # Hash should be 6 characters
        assert len(hash1) == 6

    @pytest.mark.asyncio
    async def test_collision_proof_directory_names(self, tmp_path, session_context):
        """Test that directory names include collision-proof hash."""
        storage_base = tmp_path / "storage"
        handler = _ProjectIsolationHandler(False, storage_base, True)

        with patch('pathlib.Path.cwd') as mock_cwd:
            mock_cwd.return_value = Path("/test/project")

            await handler.on_session_start("session:start", session_context)

            # Should have project_dir_name in context
            assert "project_dir_name" in session_context

            # Should follow pattern: slug-hash
            dir_name = session_context["project_dir_name"]
            assert "-" in dir_name

            parts = dir_name.split("-")
            assert len(parts) == 2
            assert parts[0] == "project"  # slug
            assert len(parts[1]) == 6     # hash

    @pytest.mark.asyncio
    async def test_different_paths_same_name_no_collision(self, tmp_path, session_context):
        """Test that projects with same name but different paths don't collide."""
        storage_base = tmp_path / "storage"
        handler = _ProjectIsolationHandler(False, storage_base, True)

        # First project at /path1/myapp
        with patch('pathlib.Path.cwd') as mock_cwd:
            mock_cwd.return_value = Path("/path1/myapp")

            context1 = session_context.copy()
            await handler.on_session_start("session:start", context1)
            dir_name1 = context1["project_dir_name"]

        # Second project at /path2/myapp
        with patch('pathlib.Path.cwd') as mock_cwd:
            mock_cwd.return_value = Path("/path2/myapp")

            context2 = session_context.copy()
            await handler.on_session_start("session:start", context2)
            dir_name2 = context2["project_dir_name"]

        # Both should have same slug but different hashes
        assert dir_name1.startswith("myapp-")
        assert dir_name2.startswith("myapp-")
        assert dir_name1 != dir_name2


class TestMetadataAndIndexing:
    """Test metadata and indexing functionality."""

    @pytest.mark.asyncio
    async def test_metadata_file_created(self, tmp_path, session_context):
        """Test that metadata.json is created on first session."""
        storage_base = tmp_path / "storage"
        handler = _ProjectIsolationHandler(False, storage_base, True)

        with patch('pathlib.Path.cwd') as mock_cwd:
            mock_cwd.return_value = Path("/test/project")

            await handler.on_session_start("session:start", session_context)

            # Find the project directory
            project_dirs = list(storage_base.glob("project-*"))
            assert len(project_dirs) == 1

            metadata_file = project_dirs[0] / "metadata.json"
            assert metadata_file.exists()

            # Verify metadata content
            import json
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            assert metadata["full_path"] == "/test/project"
            assert metadata["slug"] == "project"
            assert "first_seen" in metadata
            assert "last_accessed" in metadata

    @pytest.mark.asyncio
    async def test_metadata_updated_on_subsequent_sessions(self, tmp_path, session_context):
        """Test that metadata.json is updated on subsequent sessions."""
        storage_base = tmp_path / "storage"
        handler = _ProjectIsolationHandler(False, storage_base, True)

        with patch('pathlib.Path.cwd') as mock_cwd:
            mock_cwd.return_value = Path("/test/project")

            # First session
            await handler.on_session_start("session:start", session_context)

            # Get first_seen timestamp
            project_dirs = list(storage_base.glob("project-*"))
            metadata_file = project_dirs[0] / "metadata.json"

            import json
            with open(metadata_file, 'r') as f:
                metadata1 = json.load(f)

            first_seen1 = metadata1["first_seen"]

            # Wait a moment
            import time
            time.sleep(0.01)

            # Second session
            await handler.on_session_start("session:start", session_context)

            # Verify first_seen unchanged but last_accessed updated
            with open(metadata_file, 'r') as f:
                metadata2 = json.load(f)

            assert metadata2["first_seen"] == first_seen1
            assert metadata2["last_accessed"] != metadata1["last_accessed"]

    @pytest.mark.asyncio
    async def test_index_file_created(self, tmp_path, session_context):
        """Test that index.json is created and tracks sessions."""
        storage_base = tmp_path / "storage"
        handler = _ProjectIsolationHandler(False, storage_base, True)

        with patch('pathlib.Path.cwd') as mock_cwd:
            mock_cwd.return_value = Path("/test/project")

            await handler.on_session_start("session:start", session_context)

            # Find the project directory
            project_dirs = list(storage_base.glob("project-*"))
            index_file = project_dirs[0] / "index.json"
            assert index_file.exists()

            # Verify index content
            import json
            with open(index_file, 'r') as f:
                index = json.load(f)

            assert "sessions" in index
            assert len(index["sessions"]) == 1
            assert "session_id" in index["sessions"][0]
            assert "timestamp" in index["sessions"][0]

    @pytest.mark.asyncio
    async def test_index_tracks_multiple_sessions(self, tmp_path, session_context):
        """Test that index.json tracks multiple sessions."""
        storage_base = tmp_path / "storage"
        handler = _ProjectIsolationHandler(False, storage_base, True)

        with patch('pathlib.Path.cwd') as mock_cwd:
            mock_cwd.return_value = Path("/test/project")

            # Three sessions
            for i in range(3):
                ctx = session_context.copy()
                ctx["session_id"] = f"session-{i}"
                await handler.on_session_start("session:start", ctx)

            # Verify all sessions tracked
            project_dirs = list(storage_base.glob("project-*"))
            index_file = project_dirs[0] / "index.json"

            import json
            with open(index_file, 'r') as f:
                index = json.load(f)

            assert len(index["sessions"]) == 3

            # Verify sessions are sorted by timestamp (most recent first)
            timestamps = [s["timestamp"] for s in index["sessions"]]
            assert timestamps == sorted(timestamps, reverse=True)
