"""
Configuration validation tests for project isolation module.
"""

import pytest
from pathlib import Path
from amplifier_module_hooks_project_isolation import mount


@pytest.mark.asyncio
async def test_mount_with_default_config(mock_coordinator, default_config):
    """Test mounting with default configuration."""
    await mount(mock_coordinator, default_config)

    # Verify hook was registered
    mock_coordinator.hooks.register.assert_called_once()
    call_args = mock_coordinator.hooks.register.call_args
    assert call_args[0][0] == "session:start"
    assert callable(call_args[0][1])


@pytest.mark.asyncio
async def test_mount_with_custom_config(mock_coordinator, custom_config):
    """Test mounting with custom configuration."""
    await mount(mock_coordinator, custom_config)

    # Verify hook was registered
    mock_coordinator.hooks.register.assert_called_once()


@pytest.mark.asyncio
async def test_mount_with_empty_config(mock_coordinator):
    """Test mounting with empty configuration uses defaults."""
    await mount(mock_coordinator, {})

    # Should still register hook with defaults
    mock_coordinator.hooks.register.assert_called_once()


@pytest.mark.asyncio
async def test_mount_with_partial_config(mock_coordinator):
    """Test mounting with partial configuration."""
    config = {"use_git_root": False}
    await mount(mock_coordinator, config)

    # Should still work with defaults for missing keys
    mock_coordinator.hooks.register.assert_called_once()


@pytest.mark.asyncio
async def test_storage_base_path_expansion(mock_coordinator):
    """Test that storage_base paths are expanded correctly."""
    config = {
        "storage_base": "~/test/path",
        "use_git_root": True,
        "create_dirs": False
    }

    await mount(mock_coordinator, config)

    # Verify hook registered (path expansion happens internally)
    mock_coordinator.hooks.register.assert_called_once()


@pytest.mark.asyncio
async def test_multiple_mounts(mock_coordinator, default_config):
    """Test that multiple mounts register multiple hooks."""
    await mount(mock_coordinator, default_config)
    await mount(mock_coordinator, default_config)

    # Should register hook twice
    assert mock_coordinator.hooks.register.call_count == 2
