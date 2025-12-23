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
# Sessions stored in: ~/.amplifier/projects/api-server-a3f9d2/sessions/

# Project B
cd ~/projects/frontend-app/
amp chat
# Sessions stored in: ~/.amplifier/projects/frontend-app-7b2e8c/sessions/
```

Each project maintains separate history with collision-proof directory names.

### Scenario 2: Non-Git Projects

```bash
cd ~/scratch/experiment/
amp chat
# Sessions stored in: ~/.amplifier/projects/experiment-9d4f1a/sessions/
```

Uses directory name even without git, with path hash for uniqueness.

### Scenario 3: Nested Git Repos

```bash
cd ~/monorepo/packages/service-a/
amp chat
# Sessions stored in: ~/.amplifier/projects/monorepo-c5e2b9/sessions/
```

Uses root repository name for consistency, with unique hash.

### Scenario 4: Same Project Name, Different Locations

```bash
# First "myapp" project
cd ~/projects/myapp/
amp chat
# Sessions stored in: ~/.amplifier/projects/myapp-a3f9d2/sessions/

# Second "myapp" project (different location)
cd ~/work/myapp/
amp chat
# Sessions stored in: ~/.amplifier/projects/myapp-7b2e8c/sessions/
```

Different paths generate different hashes, preventing collisions.

## Collision-Proof Directory Naming

The module uses a hybrid approach that combines readability with collision-proofing:

**Format:** `{slug}-{hash}/`

- **Slug**: Human-readable, URL-safe project name
- **Hash**: First 6 characters of SHA-256 hash of full project path
- **Result**: Both readable AND collision-proof

### Examples

| Project Path | Directory Name |
|--------------|----------------|
| `/Users/dev/api-server` | `api-server-a3f9d2` |
| `/Users/dev/My Project` | `my-project-7b2e8c` |
| `/home/work/api-server` | `api-server-9d4f1a` (different hash!) |

### Slug Generation Rules

The readable slug portion follows these transformation rules:

| Original Name | Slug |
|---------------|------|
| `api-server` | `api-server` |
| `My Project` | `my-project` |
| `Project_Name` | `project-name` |
| `project@v2` | `projectv2` |
| `!!!` | `default` |

Slugs are:
- Lowercase
- Spaces and underscores → hyphens
- Special characters removed
- Duplicate hyphens collapsed
- Leading/trailing hyphens trimmed
- Falls back to "default" if empty

## Directory Structure

Each project gets a dedicated directory with metadata and session tracking:

```
~/.amplifier/projects/
├── api-server-a3f9d2/              # Collision-proof directory name
│   ├── metadata.json                # Project metadata
│   ├── index.json                   # Session index
│   └── sessions/                    # Session storage
│       ├── session-123.jsonl
│       └── session-456.jsonl
├── frontend-app-7b2e8c/
│   ├── metadata.json
│   ├── index.json
│   └── sessions/
│       └── session-789.jsonl
└── experiment-9d4f1a/
    ├── metadata.json
    ├── index.json
    └── sessions/
        └── session-abc.jsonl
```

### metadata.json

Each project directory contains a `metadata.json` file with project information:

```json
{
  "full_path": "/Users/dev/projects/api-server",
  "slug": "api-server",
  "git_remote": "https://github.com/user/api-server.git",
  "git_branch": "main",
  "purpose": "Amplifier CLI session",
  "first_seen": "2025-12-23T01:30:00.000000",
  "last_accessed": "2025-12-23T02:15:00.000000"
}
```

**Fields:**
- `full_path`: Absolute path to the project directory
- `slug`: Human-readable slug generated from directory name
- `git_remote`: Git remote URL (if in a git repository)
- `git_branch`: Current git branch (if in a git repository)
- `purpose`: Session purpose from context (default: "Amplifier CLI session")
- `first_seen`: ISO timestamp of first session
- `last_accessed`: ISO timestamp of most recent session (updated each time)

### index.json

Each project directory maintains an `index.json` file tracking all sessions:

```json
{
  "sessions": [
    {
      "session_id": "session-456",
      "timestamp": "2025-12-23T02:15:00.000000",
      "message_count": 15
    },
    {
      "session_id": "session-123",
      "timestamp": "2025-12-23T01:30:00.000000",
      "message_count": 8
    }
  ]
}
```

**Features:**
- Sessions sorted by timestamp (most recent first)
- Tracks session ID, timestamp, and message count
- Appended to on each session start
- Provides historical view of project activity

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
