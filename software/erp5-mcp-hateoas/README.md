# ERP5 MCP Server — SlapOS Software Release

Deploy an ERP5 MCP (Model Context Protocol) server as a SlapOS service with
HAProxy frontend and log rotation.

## Architecture

```
                 ┌─────────────────────────────────────────┐
                 │           SlapOS Partition               │
                 │                                          │
  Client ──────►│  HAProxy (:8765/ipv6) ──► uvicorn (:18765/ipv6)  │
  (Claude, etc.) │  - SSE timeout 4h         - erp5_mcp_server     │
                 │  - health checks          - WatchedFileHandler   │
                 │  - access logging           logs to var/log/     │
                 │                                          │
                 │  logrotate (daily cron)                  │
                 │  - rotates mcp + haproxy logs            │
                 │  - compresses, keeps N days              │
                 └─────────────────────────────────────────┘
                            │
                            ▼
                    ERP5 Instance (API)
```

## Files

| File | Purpose |
|------|---------|
| `software.cfg` | Software Release — installs Python deps, HAProxy, logrotate |
| `instance.cfg.in` | Instance dispatch (Jinja2) — routes to the right profile |
| `instance-erp5-mcp.cfg.in` | Instance buildout — defines all services and config |
| `instance-input-schema.json` | JSON Schema for instance parameters (SlapOS Master UI) |

## Instance Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `mcp-port` | `8765` | External port (HAProxy frontend) |
| `mcp-internal-port` | `18765` | Internal port (uvicorn, not exposed) |
| `erp5-url` | — | Base URL of ERP5 instance (required) |
| `erp5-username` | — | ERP5 API user (required) |
| `erp5-password` | — | ERP5 API password (required, passed via env var) |
| `mcp-workers` | `1` | Number of uvicorn worker processes |
| `mcp-log-level` | `info` | Logging level: debug/info/warning/error |
| `logrotate-num` | `30` | Days of logs to retain |

## Requesting an Instance

```bash
slapos request erp5-mcp-instance \
  software_release=https://lab.nexedi.com/.../software.cfg \
  --parameters '{
    "erp5-url": "https://erp5.example.com",
    "erp5-username": "mcp-user",
    "erp5-password": "s3cret",
    "mcp-port": 8765,
    "mcp-log-level": "info"
  }'
```

## Design Decisions

### Why HAProxy in front?
- **SSE support**: MCP uses Server-Sent Events which need long-lived connections.
  HAProxy's `timeout tunnel 4h` handles this properly.
- **TLS termination**: When adding `caucase` certificates later, no Python code changes needed.
- **Health checks**: HAProxy monitors `/health` and removes unhealthy backends.
- **Standard SlapOS pattern**: Consistent with other SlapOS software releases.

### Why WatchedFileHandler for logging?
Python's `WatchedFileHandler` detects when the log file has been rotated (inode changes)
and automatically reopens it. This means logrotate can use the standard move-and-create
approach without needing a post-rotate signal (`SIGUSR1`). This is simpler and more
reliable than `copytruncate`.

### IPv6
Both HAProxy and uvicorn bind directly to the partition's IPv6 address
(`ipv6-random` from `slapconfiguration`). No IPv4-to-IPv6 translation needed.
If IPv4 access is required, uncomment the IPv4 bind line in the HAProxy config.

## Adapting to Your MCP Server

The instance profile assumes your MCP server is importable as:

```python
# erp5_mcp_server/main.py
from mcp.server.sse import SseServerTransport
# ... your MCP server code ...
app = create_app()  # Returns an ASGI app (Starlette/FastAPI)
```

Adjust the `command-line` in `[erp5-mcp-service]` to match your entry point:

```ini
# If it's a module:
command-line = uvicorn erp5_mcp_server.main:app ...

# If it's a script:
command-line = python -m erp5_mcp_server ...
```

Your server should expose a `/health` endpoint returning HTTP 200 for HAProxy
health checks:

```python
@app.get("/health")
async def health():
    return {"status": "ok"}
```

## Adding TLS (Future)

To add TLS via `caucase` (SlapOS certificate authority):

1. Extend `software.cfg` with `../../component/caucase/buildout.cfg`
2. Add a `[caucase-updater]` section to request certificates
3. Update HAProxy `bind` to: `bind [ipv6]:port ssl crt /path/to/cert.pem`
4. Update published URLs to `https://`
