# LanguageTool

[LanguageTool](https://languagetool.org/) is an open source grammar and style
checker. This software release downloads the standalone LanguageTool
distribution and runs the HTTP server.

The HTTP server listens only on the IPv6 address of the instance partition.
The instance requests a shared frontend and publishes a public HTTPS URL.

The instance publishes these connection parameters:

- `url`: the public HTTPS URL of the LanguageTool HTTP server.
- `backend-url`: the IPv6 URL of the HTTP server. Only reachable from the
  partition network.
- `monitor-base-url`: the base URL of the instance monitor.
- `monitor-setup-url`: a link to add the instance to a monitoring interface.

## API

The server exposes the LanguageTool HTTP API. Use the published `url`
parameter or the `backend-url` parameter:

```sh
curl -s -X POST "$url/v2/check" \
  -d "language=en-US" \
  -d "text=I has an error."
```

## Tests

The automated tests live in `test/`. They deploy an instance and check the
HTTP API. See `test/README.md`.
