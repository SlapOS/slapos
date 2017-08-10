caucase - CA for Users, CA for SErvices

Slapos integration
==================

This software release library provides macros to help you integrate caucase
into your software release.

`buildout.cfg` declares caucase dependencies.

`instance-caucase.cfg.jinja2.in` declares jinja2 macros to deploy client and
server components of caucase.

Software
--------

This declares the following sections:

(TODO)

Server
------

Macro::
  caucased(prefix, caucased_path, data_dir, netloc, service_auto_approve_count=0, key_len=None, promise=None)

This macro produces the following sections which you will want to reference so
they get instanciated:

- `<prefix>`: Creates `<caucased>` executable file to start `caucased`,
  and `<data_dir>` directory for its data storage needs.
  `caucased` will listend on `netloc`, which must be of the format
  `hostname[:port]`, where hostname may be an IPv4 (ex: `127.0.0.1`), an IPv6
  (ex: `[::1]`), or a domain name (ex: `localhost`). Port, when provided, must
  be numeric. If port is not provided, it default to `80`.

  If port is `80`, `caucased` will listen on `80` and `443` for given
  hostname. This is *not* the recommended usage.

  If port is not `80`, `caucased` will listen on it *and* its immediate next
  higher port (ex: `[::1]:8009` will listen on both `[::1]:8009` and
  `[::1]:8010`). This is the recommended usage.

- `<prefix>-promise`: (only produced if `<promise>` is not None). Creates an
  executable at the path given in `<promise>`, which will attempt to connect to
  caucase server, and fail if it detects any anomaly (port not listening,
  protocol error, certificate discrepancy...).

Client
------

(TODO)
