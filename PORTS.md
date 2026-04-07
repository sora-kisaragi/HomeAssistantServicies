# Port Allocation

This file is the single source of truth for port assignments.
Check here before adding a new service to avoid conflicts.

| Port | Service           | Notes                        |
|------|-------------------|------------------------------|
| 3000 | playwright-mcp    | MCP server (browser automation) |
| 8080 | searxng           | Privacy-respecting metasearch |
| 8765 | discovery-api     | Service discovery API        |
| 9000 | (reserved)        | Spare / webhook listener     |
