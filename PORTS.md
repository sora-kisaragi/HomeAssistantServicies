# Port Allocation

This file is the single source of truth for port assignments.

Check here before adding a new service to avoid conflicts.

| Port | Service           | Notes                                      |
|------|-------------------|--------------------------------------------|
| 3000 | playwright-mcp    | MCP server (browser automation)            |
| 8080 | searxng           | Privacy-respecting metasearch              |
| 8765 | discovery-api     | Service discovery API                      |
| 8767 | watcher-ui        | Service management dashboard               |
| 9000 | (reserved)        | Spare / webhook listener                   |
| 9001 | faster-whisper    | STT — on-demand, GPU required              |
| 9002 | qwen-tts          | TTS — on-demand, GPU required              |
| 9003–9099 | (reserved) | Future GPU / on-demand services            |
