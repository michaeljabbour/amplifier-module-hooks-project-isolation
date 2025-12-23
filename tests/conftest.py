"""
Pytest configuration and fixtures for project isolation tests.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock


@pytest.fixture
def mock_coordinator():
    """Mock Amplifier coordinator for testing."""
    coordinator = Mock()
    coordinator.hooks = Mock()
    coordinator.hooks.register = Mock()
    return coordinator


@pytest.fixture
def default_config():
    """Default configuration for testing."""
    return {
        "use_git_root": True,
        "storage_base": "~/.amplifier/projects",
        "create_dirs": True
    }


@pytest.fixture
def custom_config():
    """Custom configuration for testing."""
    return {
        "use_git_root": False,
        "storage_base": "~/custom/storage",
        "create_dirs": False
    }


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project directory."""
    project = tmp_path / "test-project"
    project.mkdir()
    return project


@pytest.fixture
def session_context():
    """Default session context for testing."""
    return {
        "session_id": "test-session-123",
        "user": "test-user"
    }
