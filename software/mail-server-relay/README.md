# mail-server-relay

- This can be set up to act as a relay for the `mail-server` SR (which would host an actual mail server) and an external mail delivery service (such as SMTP2go, Sendgrid, Brevo, ...).
- The original purpose was bridging IPv6-only nodes to IPv4-only delivery services, but the end goal is allowing a many-to-many setup between mail server, relays, and delivery services (with potential for load balancing, ...).
