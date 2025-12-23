# amplifier-module-hooks-project-isolation

Per-project session storage for Amplifier CLI applications.

## Overview

This module provides automatic project isolation for Amplifier sessions. When enabled, each project gets its own session storage directory, allowing you to maintain separate conversation histories across different projects.

## Features

- **Automatic Detection**: Uses git repository root or current working directory
- **Slug Generation**: Creates human-readable project slugs from directory names
- **Fallback Strategy**: Falls back to CWD if not in a git repository
- **Configurable Storage**: Control where project sessions are stored
- **Zero Configuration**: Works out of the box with sensible defaults

## How It Works

1. **Session Start**: Hook intercepts session creation
2. **Project Detection**: Determines project root (git root or CWD)
3. **Slug Generation**: Creates slug from project directory name
4. **Storage Path**: Sets session storage to `~/.amplifier/projects/<slug>/sessions/`
5. **Isolation**: Each project maintains its own conversation history

## Installation

Add to your bundle's hooks section:

```yaml
hooks:
  - module: hooks-project-isolation
    source: git+https://github.com/yourusername/amplifier-module-hooks-project-isolation@main
    config:
      use_git_root: true
      storage_base: ~/.amplifier/projects
      create_dirs: true
```

Or install locally for development:

```yaml
hooks:
  - module: hooks-project-isolation
    source: git+file:///path/to/amplifier-module-hooks-project-isolation
    config:
      use_git_root: true
      storage_base: ~/.amplifier/projects
      create_dirs: true
```

## Configuration

### `use_git_root` (boolean, default: true)

Use git repository root for project detection. Falls back to CWD if not in a git repo.

```yaml
use_git_root: true   # Use git root (recommended)
use_git_root: false  # Always use CWD
```

### `storage_base` (string, default: "~/.amplifier/projects")

Base directory for project session storage.

```yaml
storage_base: ~/.amplifier/projects  # Default
storage_base: ~/work/sessions        # Custom location
```

### `create_dirs` (boolean, default: true)

Automatically create storage directories if they don't exist.

```yaml
create_dirs: true   # Auto-create (recommended)
create_dirs: false  # Manual directory management
```

## Usage Examples

### Scenario 1: Multiple Git Projects

```bash
# Project A
cd ~/projects/api-server/
amp chat
# Sessions stored in: ~/.amplifier/projects/api-server/sessions/

# Project B
cd ~/projects/frontend-app/
amp chat
# Sessions stored in: ~/.amplifier/projects/frontend-app/sessions/
```

Each project maintains separate history.

### Scenario 2: Non-Git Projects

```bash
cd ~/scratch/experiment/
amp chat
# Sessions stored in: ~/.amplifier/projects/experiment/sessions/
```

Uses directory name even without git.

### Scenario 3: Nested Git Repos

```bash
cd ~/monorepo/packages/service-a/
amp chat
# Sessions stored in: ~/.amplifier/projects/monorepo/sessions/
```

Uses root repository name for consistency.

## Project Slug Generation

The module generates URL-safe slugs from project directory names:

| Directory Name | Generated Slug |
|----------------|----------------|
| `api-server` | `api-server` |
| `My Project` | `my-project` |
| `Project_Name` | `project-name` |
| `project@v2` | `project-v2` |

Slugs are:
- Lowercase
- Alphanumeric + hyphens only
- No special characters
- Human-readable

## Directory Structure

When using default configuration, sessions are organized as:

```
~/.amplifier/projects/
├── api-server/
│   └── sessions/
│       ├── session-123.jsonl
│       └── session-456.jsonl
├── frontend-app/
│   └── sessions/
│       └── session-789.jsonl
└── experiment/
    └── sessions/
        └── session-abc.jsonl
```

## Architecture

This module follows official Amplifier module conventions:

- **Entry Point**: `async def mount(coordinator, config)`
- **Hook Registration**: Registers `session:start` hook via coordinator
- **Module Type**: Hook module (`__amplifier_module_type__ = "hook"`)
- **Dependencies**: Zero dependencies (self-contained)
- **Testing**: pytest with `asyncio_mode = "strict"`

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/yourusername/amplifier-module-hooks-project-isolation.git
cd amplifier-module-hooks-project-isolation

# Install dependencies
pip install -e ".[dev]"
```

### Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=amplifier_module_hooks_project_isolation
```

### Project Structure

```
amplifier-module-hooks-project-isolation/
├── amplifier_module_hooks_project_isolation/
│   └── __init__.py                    # Module implementation
├── tests/
│   ├── conftest.py                    # Test fixtures
│   ├── test_validation.py             # Config validation tests
│   └── test_behavioral.py             # Behavioral tests
├── pyproject.toml                     # Package metadata
├── LICENSE                            # MIT License
├── README.md                          # This file
├── CODE_OF_CONDUCT.md                 # Community guidelines
├── SECURITY.md                        # Security policy
└── SUPPORT.md                         # Support resources
```

## Contributing

Contributions are welcome! Please:

1. Read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
2. Check [existing issues](../../issues)
3. Create an issue before major changes
4. Follow existing code style
5. Add tests for new features
6. Update documentation

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

See [SUPPORT.md](SUPPORT.md) for help and community resources.

## Acknowledgments

Built for the [Amplifier](https://github.com/microsoft/amplifier) ecosystem.
