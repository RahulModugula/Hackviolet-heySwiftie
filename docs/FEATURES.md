# heySwiftie v0.6.0 Features

## Conversation Intelligence

### Full-Text Search
Search across all your conversations with relevance-ranked results. Find that important discussion from weeks ago instantly.

```bash
POST /api/search/conversations
{"query": "python project", "limit": 20}
```

### Mood Timeline
Track your emotional patterns over time. See how your sentiment changes across conversations.

```bash
GET /api/features/mood/timeline?limit=10
```

## Memory & Insights

### Habit Detection
Automatically detects recurring topics in your conversations. Get insights about what you're consistently interested in.

```bash
GET /api/features/habits
```

### Knowledge Graph
Facts about you are stored in a relationship graph. Ask Swiftie to find related facts across topics.

## Data Management

### Export & Backup
Full JSON exports of conversations, memories, and facts. Secure your data.

```bash
GET /api/features/export/all
```

### Redis Caching
Sessions are cached for fast retrieval. Rate limiting protects against abuse.

## Developer Features

### Plugin System
Extend Swiftie with custom tools. Drop Python files in `./plugins/` and they auto-load.

```python
# plugins/my_tool.py
async def register_tools(tool_registry):
    tool_registry.register(ToolDefinition(...))

PLUGIN = type('Plugin', (), {
    'name': 'my_tool',
    'register_tools': register_tools,
})()
```

### MCP Server
IDE integration for Claude Code, Cursor, and other tools supporting the Model Context Protocol.

## Intelligence

### Smart Reminders
Context-aware reminders based on your tasks, habits, and conversation patterns.

```bash
GET /api/features/reminders
```

### Daily Digest
Morning briefing with activity summary, pending tasks, and suggestions.

```bash
GET /api/features/daily-digest
```

### Context Pruning
Intelligent conversation window management keeps context relevant and within token limits.
