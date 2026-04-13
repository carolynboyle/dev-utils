# project_structure.md

**Path:** python/mcpkit/docs/project_structure.md
**Syntax:** markdown
**Generated:** 2026-04-13 13:55:31

```markdown
dev-utils/
└── python/
    └── mcpkit/
        ├── README.md
        ├── pyproject.toml
        │
        ├── src/mcpkit/
        │   ├── __init__.py
        │   │
        │   ├── server.py
        │   │   └── MCPServer class
        │   │       - loads config.yaml
        │   │       - registers tools from YAML
        │   │       - starts MCP server
        │   │
        │   ├── tool_registry.py
        │   │   └── ToolRegistry class
        │   │       - parses tools.yaml
        │   │       - maps handler strings to functions
        │   │       - validates tool schemas
        │   │
        │   ├── executor.py
        │   │   └── Executor class
        │   │       - calls handler functions
        │   │       - error handling
        │   │       - logging
        │   │
        │   ├── workflow.py
        │   │   └── Workflow class
        │   │       - parses workflow.yaml
        │   │       - orchestrates step execution
        │   │       - approval gates (manual/pending)
        │   │
        │   ├── handlers/
        │   │   ├── __init__.py
        │   │   ├── builtins.py
        │   │   │   - read_yaml()
        │   │   │   - read_file()
        │   │   │   - write_file()
        │   │   │   - list_files()
        │   │   └── models.py
        │   │       - call_ollama()
        │   │       - call_generic_llm()
        │   │
        │   ├── config.py
        │   │   └── Config class
        │   │       - loads config.yaml
        │   │       - validates required fields
        │   │
        │   └── exceptions.py
        │       - MCPKitError
        │       - HandlerNotFoundError
        │       - ValidationError
        │
        └── tests/
            ├── test_server.py
            ├── test_registry.py
            ├── test_executor.py
            └── test_workflow.py
```
