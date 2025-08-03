# Contributing to heySwiftie

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

```bash
git clone https://github.com/RahulModugula/heyswiftie
cd heyswiftie
pip install -e ".[dev,voice]"
```

## Code Style

We use Ruff for linting and formatting:

```bash
make lint  # Check style
make fmt   # Auto-format
```

## Testing

All contributions should include tests:

```bash
make test
```

Target areas for new tests:
- Core features in `app/core/`
- New API routes
- Memory operations
- RAG retrieval

## Adding Features

1. **Feature Planning**: Open an issue first to discuss approach
2. **Implementation**: Create feature in appropriate module
3. **Tests**: Add tests in `tests/test_*.py`
4. **Documentation**: Update relevant docs
5. **Commit**: Use clear commit messages

### Example: Adding a New Tool

```python
# app/core/tools.py - add handler
async def _my_tool_handler(input: str) -> str:
    return f"Result: {input}"

# In ToolRegistry._register_builtins()
self.register(ToolDefinition(
    name="my_tool",
    description="Do something useful",
    parameters={"type": "object", "properties": {"input": {"type": "string"}}},
    handler=_my_tool_handler,
))

# tests/test_tools.py - add test
def test_my_tool():
    registry = ToolRegistry()
    tool = registry.get("my_tool")
    assert tool is not None
```

### Example: Adding a Plugin

1. Create `plugins/my_feature.py`
2. Implement `register_tools()` function
3. Define `PLUGIN` object
4. Tests auto-run plugin loading

```python
# plugins/my_feature.py
from app.core.tools import ToolDefinition

async def my_handler(param: str) -> str:
    return f"Done: {param}"

async def register_tools(tool_registry):
    tool_registry.register(ToolDefinition(...))

PLUGIN = type('MyFeature', (), {
    'name': 'my_feature',
    'version': '0.1.0',
    'description': 'My cool feature',
    'register_tools': register_tools,
})()
```

## Architecture Principles

- **Modularity**: Each feature in its own module
- **Dependency Injection**: Wire components in `dependencies.py`
- **Graceful Degradation**: Optional features (reranker, Redis) fail safely
- **Async-first**: Use async/await throughout
- **Tests First**: Write tests before features

## Documentation

Update relevant docs when adding features:

- `docs/FEATURES.md` - User-facing feature overview
- `docs/ARCHITECTURE.md` - System design
- `docs/INSTALLATION.md` - Setup instructions
- `README.md` - High-level overview

## Commit Messages

Use clear, descriptive commit messages:

```
add feature description in lowercase

More detail if needed. Reference issues like #123.
```

Examples:
- `add mood tracking over time`
- `fix knowledge graph traversal depth limit`
- `improve rag relevance scoring`

## PRs & Reviews

- Open a pull request with your changes
- Link related issues
- Include test coverage
- Wait for maintainer review

## Questions?

Open an issue or discussion. The maintainer is responsive!

---

**Thanks for contributing to heySwiftie!** 🎉
