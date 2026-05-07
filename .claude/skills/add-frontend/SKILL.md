# Request an IPv4 Frontend for a Service

TRIGGER when: the user asks to add a frontend, CDN, or public URL to a SlapOS service, OR you need to expose an instance's internal service via an external HTTPS URL.

Generate the buildout sections to request a shared apache-frontend instance, add a health-check promise, and publish the resulting CDN URL.

## Arguments

**$ARGUMENTS** — which service to front (service name, backend URL section), which instance profile. If empty, ask the user which service needs a frontend.

## Background — SlapOS Frontend Architecture

SlapOS services typically listen on IPv6 addresses that are not directly accessible from the public internet. To expose a service via a public HTTPS URL, you request a **shared** (slave) instance of the `apache-frontend` software release. This creates a reverse proxy entry that forwards traffic from a CDN domain to your service's internal URL.

The frontend request uses `slapos.cookbook:requestoptional` (not `slapos.cookbook:request`) to avoid failing the entire instance if the frontend is temporarily unavailable.

Reference: https://handbook.rapid.space/user/rapidspace-HowTo.Automatically.Request.An.Ipv4.Frontend.For.Your.Service

**Prerequisite:** The monitoring stack must be extended in the software release (see `/add-monitoring`). The `monitor-promise-base` section is needed for the URL check promise.

## Step-by-step procedure

### Step 1 — Identify the backend URL

Read the instance `.cfg.in` to find the section that provides the service's access URL. This is typically an IPv6 URL like:
```ini
[my-service]
access_url = http://[${slap-configuration:ipv6-random}]:${:port}
```

### Step 2 — Add the frontend request section

In the instance `.cfg.in` file, add:

```ini
[my-service-frontend]
<= slap-connection
recipe = slapos.cookbook:requestoptional
name = My Service frontend
software-url = http://git.erp5.org/gitweb/slapos.git/blob_plain/HEAD:/software/apache-frontend/software.cfg
shared = true
config-url = ${my-service:access_url}
config-https-only = true
return = domain secure_access
```

Key properties:
- `<= slap-connection` — inherits SlapOS connection parameters (server URL, partition, etc.)
- `recipe = slapos.cookbook:requestoptional` — does not fail if frontend is unavailable
- `shared = true` — requests a slave/shared instance (not a full partition)
- `config-url` — the backend URL to proxy to
- `config-https-only = true` — redirect HTTP to HTTPS
- `return` — connection parameters to retrieve from the frontend (`domain`, `secure_access`)

### Step 3 — Add a health-check promise

Add a promise to verify the frontend URL is accessible:

```ini
[my-service-frontend-promise]
<= monitor-promise-base
promise = check_url_available
name = my-service-http-frontend.py
url = ${my-service-frontend:connection-secure_access}
config-url = ${:url}
config-check-secure = 1
```

### Step 4 — Publish the frontend URL

Add the CDN URL to `[publish-connection-information]`:

```ini
[publish-connection-information]
...existing publications...
server-cdn-url = ${my-service-frontend-promise:url}
```

### Step 5 — Add to buildout parts

Ensure the frontend and promise sections are in the parts list:

```ini
[buildout]
parts =
  ...existing parts...
  my-service-frontend
  my-service-frontend-promise
```

## Additional frontend configuration options

```ini
# Custom domain
config-custom_domain = my-custom-domain.example.com

# Specific type (e.g., websocket)
config-type = websocket

# Disable HTTPS redirect
config-https-only = false
```

## After generating

1. Run `/reprocess-instance` to deploy the frontend request
2. The frontend takes a few minutes to propagate — run the request script repeatedly until `server-cdn-url` appears in connection parameters
3. Access the CDN URL in a browser to verify
