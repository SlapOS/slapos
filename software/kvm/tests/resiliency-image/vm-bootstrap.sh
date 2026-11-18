#!/bin/bash
set -e

mkdir -p /var/lib/kvm-resiliency-kv /usr/local/bin

cat > /usr/local/bin/kvm-resiliency-kv-server.py <<'PYEOF'
#!/usr/bin/env python3
import http.server
import urllib.parse

STORE = '/var/lib/kvm-resiliency-kv/key'


class Handler(http.server.BaseHTTPRequestHandler):
  def do_GET(self):
    parsed = urllib.parse.urlparse(self.path)
    if parsed.path == '/get':
      try:
        with open(STORE) as f:
          value = f.read()
      except FileNotFoundError:
        value = ''
    elif parsed.path == '/set':
      value = urllib.parse.parse_qs(parsed.query).get('key', [''])[0]
      with open(STORE, 'w') as f:
        f.write(value)
        f.flush()
        import os
        os.fsync(f.fileno())
    else:
      self.send_response(404)
      self.end_headers()
      return
    body = value.encode()
    self.send_response(200)
    self.send_header('Content-Length', str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def log_message(self, format, *args):
    pass


if __name__ == '__main__':
  # the kvm software release's own NAT rules forward external port
  # 10080 to port 80 inside the guest (see nat-rules in
  # instance-kvm.cfg.jinja2), so the test's get/set client on port
  # 10080 reaches this server here, on the guest's own port 80.
  http.server.HTTPServer(('0.0.0.0', 80), Handler).serve_forever()
PYEOF

chmod +x /usr/local/bin/kvm-resiliency-kv-server.py

cat > /etc/systemd/system/kvm-resiliency-kv.service <<'EOF'
[Unit]
Description=KVM resiliency test get/set key-value server
After=network.target

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/kvm-resiliency-kv-server.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now kvm-resiliency-kv.service
