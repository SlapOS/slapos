# Headless Chromium
This software release compiles and runs a headless Chromium shell and
exposes an interface to connect to it remotely from another browser.

After deployment, the instance is configured like this:

```
   Rapid CDN Frontend
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
The following instance parameters can be configured:

- target-url:             URL for Chromium to load on startup.
- remote-debugging-port:  Port for Chromium to listen on.
- nginx-proxy-port:       Port for Ningx proxy to listen on.
- monitor-httpd-port:     Port for monitor.
- incognito:              Force Incognito mode
- window-size:            Initial window size
- block-new-web-contents: Block new web contents

See `instance-headless-chromium-input-schema.json` for default values.
