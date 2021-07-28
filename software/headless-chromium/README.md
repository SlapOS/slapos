# Headless Chromium
This software release compiles and runs a headless Chromium shell and
exposes an interface to connect to it remotely from another browser.

After deployment, the instance is configured like this:

```
   Caddy frontend
     |
   (HTTPS, IPv6)
     |
   Nginx proxy, basic authentication
     |
   (HTTP, IPv4)
     |
   Chromium shell
```

The proxy is necessary because Chromium only accepts local connections
for remote debugging.

## Parameters
The options that you can set at the command line when requesting an
instance are:

- target-url:             URL for Chromium to load on startup.
- remote-debugging-port:  Port for Chromium to listen on.
- nginx-port:             Port for Ningx proxy to listen on.
- monitor-port:           Port for monitor.

Defaults are set in instance.cfg.in.
