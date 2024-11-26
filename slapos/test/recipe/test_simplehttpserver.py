import errno
import os
import shutil
import tempfile
import unittest
import socket
import subprocess
import time
import warnings

from six.moves.urllib import parse as urlparse
import requests

from slapos.recipe import simplehttpserver
from slapos.test.utils import makeRecipe

CERTIFICATE_FOR_TEST = """
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC8/zt/ndbvsCXb
2Kf5CaYlSsngykwfeeekDSoYHqWrl/WltFbdz/yw1ggRZUXo0l1ueJrDWqQzZIAT
9YjoNkX3G21nEIzg9/aKqq1vqHKBH+JaaAt+m84GnErFDztnkiMUKWFKyFmseg0O
QtkYGw179bXfcXX2x18gz8aBmCkjBjKjfiQtYWs9sPU0grBl9rE+h1maRh2uQXnF
BTMKHJ6wNGyFgg0ATqrBiLRv+wxCnuCdGzJzkZ3ytKuhqkwEcEIsVHSSwAx+hdBR
3AUBl1jfwUukj8a4rf23RR3pvYIZiMEdalsuiLBKyjzCqSPo5VZzSWSiK5CTPspM
4bz9OXPHAgMBAAECggEAMQcg/y0J+em/GHXutSrsn9Xz4s13y96K2cLUfadNoOLt
xYuv0SDIU3NiamjUJt6TgDnnI/Bakj5q/0J9vod9xOmnisn/Ucjhev1luoZ/FcIY
rQ06liCC5LIcr1wRM//z+6H0bDrnEFglFOMAgEFcUSDfilRbnqX/pnpf63R2j2/0
ttsSI3/plJAJbGha01S9jLTRKqHWy0vV0XJUXWkg0BETJci0w4fJ1kdMmnELaq4L
kU8IZoHwbRq/RBudQoN4ceZjUnMFcVSQCFa+5coYEJvrYvcrLzA8E01435AGyHyv
DzkiYwIrAzfQYhNVKLXgXrMGclNk8k9SMISSpVq92QKBgQDtJZjWrKxz5iWheIe8
uGM2rQ7ZgtAO9pYhDNXwKvlxEEXQrtWrVT2KA02/rbyOGoB4D7hlJXlopSLenV3o
5d3lRXhIXHSz2Qzy5/opPK0rt6TBXKWZ3+AxV7lpzJReltgRSn6mg1bgB2D14GYa
1gfH1W2fVJ2B5LrB3dPOCJOC4wKBgQDMBbEBsUh1HSAN9tR9icZcgYD2/1aYVHVJ
bnGUR1xs1cQRHKZZn6y/BBy021YAGIbgbFb8YhJC5lCMmeLADho3W1XxYhe6ssiE
E4sbK4y+fD2MFvAe7Y//IB0KRmAzTG3tPyOjBMftAMwrGoXIo990BAFtrO8tTIeb
9XcUnd0MzQKBgA8jz1YlP/1GPDDK2R+bRfo/oisQxuetpngFscLbe4FUYKCqCMof
bwZYn6YVGWyZFIqVtlf+xHmB0XAU6+HqivgQL1WvUWQJ/2Ginb30OboIx2Pw3kGs
oUuFJjky7mX7i1/POba3u9whnHcWFG6yK1z+qzj41fVs/N9ToioNMh2xAoGAIAY4
rYpVVES5FlgLLJVmtHiDdMHJpumC637RhzPYVyEKwKDdn63HoMgVdXIEQsmWyj1X
PhBqy2N5e0hgZkMQbGYCzHvYO676eHjU2fPxCKlZw9aJ5GDnvGUfCdDYItU5YAcM
IfeLJjF82rs0CrVmSsCiNMPzWwnrM1jJU0wgOXUCgYEAzAu7kDTITpMBvtUxWapQ
c1YoE4CqCG6Kq+l65SDe+c9VCckEmVPEhHbPmTv28iUh9n5MipCi7tehok2YX/Cw
o8M12F9A9sOWTqrNylCgIjU0GCTBkA5LvYV786TYJgWPZ5Mwdkmq5Ifbf3Ti/uGk
z6Cids97LVTVrV4iAZ+alY0=
-----END PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
MIIDXzCCAkegAwIBAgIUAXy1ly1SQ41kXIKV2orz+SghlrUwDQYJKoZIhvcNAQEL
BQAwPjELMAkGA1UEBhMCRVUxDzANBgNVBAoMBk5leGVkaTEeMBwGA1UEAwwVdGVz
dF9zaW1wbGVodHRwc2VydmVyMCAXDTI0MTIwMjE0MTkzNVoYDzIxMDcwMTIyMTQx
OTM1WjA+MQswCQYDVQQGEwJFVTEPMA0GA1UECgwGTmV4ZWRpMR4wHAYDVQQDDBV0
ZXN0X3NpbXBsZWh0dHBzZXJ2ZXIwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEK
AoIBAQC8/zt/ndbvsCXb2Kf5CaYlSsngykwfeeekDSoYHqWrl/WltFbdz/yw1ggR
ZUXo0l1ueJrDWqQzZIAT9YjoNkX3G21nEIzg9/aKqq1vqHKBH+JaaAt+m84GnErF
DztnkiMUKWFKyFmseg0OQtkYGw179bXfcXX2x18gz8aBmCkjBjKjfiQtYWs9sPU0
grBl9rE+h1maRh2uQXnFBTMKHJ6wNGyFgg0ATqrBiLRv+wxCnuCdGzJzkZ3ytKuh
qkwEcEIsVHSSwAx+hdBR3AUBl1jfwUukj8a4rf23RR3pvYIZiMEdalsuiLBKyjzC
qSPo5VZzSWSiK5CTPspM4bz9OXPHAgMBAAGjUzBRMB0GA1UdDgQWBBQc1p1Qudnk
WcxOnVt+4zw+MpmOITAfBgNVHSMEGDAWgBQc1p1QudnkWcxOnVt+4zw+MpmOITAP
BgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQCjZfuToaybR8JqTQ1l
4MZ8BEzFlq6Ebn8x4shiWc3wiX5cd1RSF4iilpDv2yp9MNiTHXkMxNEnx9NMdK/+
0bNlBn6tcv5MLZynXQnT+keJ73iYFB0Og298NauEQPI9x5/gf3zVGKBJ7d/aOumR
VRUugFQLzwWj27Muh1rbdayh73gpuNm1ZF+HgwWy8vYc5XoLS3gZ+tlGX3Im0Agg
ug2Kng5JY+f1aC8ZWBtTTFa2k2QALD1dD+vzGsoKitUEarg1CMHO/f6VsAFTfJT3
NDI4ky4bVMpkq17t65YXf1QVgquOEPfAnkzn51/vPzvezOMzPYQbsQqMbc4jehZT
oxpd
-----END CERTIFICATE-----
""".strip()


class SimpleHTTPServerTest(unittest.TestCase):
  process = None

  def setUp(self):
    self.base_path = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.base_path)
    self.install_dir = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.install_dir)
    self.wrapper = os.path.join(self.install_dir, 'server')
    self.process = None

  def setUpRecipe(self, opt=None):
    opt = opt or {}
    self.certfile = opt.get('cert-file')
    if not 'socketpath' in opt and not 'abstract' in opt:
      opt['host'] = host = os.environ['SLAPOS_TEST_IPV4']
      opt['port'] = port = 9999
      scheme = 'https' if self.certfile else 'http'
      self.server_url = scheme + '://{}:{}'.format(host, port)
    else:
      self.server_url = None
    options = {
        'base-path': self.base_path,
        'log-file': os.path.join(self.install_dir, 'simplehttpserver.log'),
        'wrapper': self.wrapper,
    }
    options.update(opt)
    self.recipe = makeRecipe(
        simplehttpserver.Recipe,
        options=options,
        name='simplehttpserver',
    )

  def startServer(self):
    self.assertEqual(self.recipe.install(), self.wrapper)
    self.process = subprocess.Popen(
        self.wrapper,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True, # BBB Py2, use text= in Py3
    )
    if self.server_url:
      kwargs = {'verify': False} if self.certfile else {}
      def check_connection():
        resp = requests.get(self.server_url, **kwargs)
        self.assertIn('Directory listing for /', resp.text)
      ConnectionError = requests.exceptions.ConnectionError
      cleanup = None
    else:
      address = self.recipe.options['address']
      s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
      def check_connection():
        s.connect(address)
      ConnectionError = socket.error
      cleanup = lambda: s.close()
    try:
      for i in range(16):
        try:
          check_connection()
          break
        except ConnectionError:
          time.sleep(i * .1)
      else:
        # Kill process in case it did not crash
        # otherwise .communicate() may hang forever.
        self.process.terminate()
        self.process.wait()
        self.fail(
          "Server did not start\n"
          "out: %s\n"
          "err: %s"
          % self.process.communicate())
    finally:
      if cleanup:
        cleanup()
    return self.server_url

  def tearDown(self):
    if self.process:
      self.process.terminate()
      self.process.wait()
      self.process.communicate() # close pipes
      self.process = None

  def write_should_fail(self, url, hack_path, hack_content):
    # post with multipart/form-data encoding
    resp = requests.post(
        url,
        files={
            'path': hack_path,
            'content': hack_content,
        },
    )
    # First check for actual access to forbidden files
    try:
      with open(hack_path) as f:
        content = f.read()
      if content == hack_content:
        self.fail(content)
      self.fail("%s should not have been created" % hack_path)
    except IOError as e:
      if e.errno != errno.ENOENT:
        raise
    # Now check for proper response
    self.assertEqual(resp.status_code, requests.codes.forbidden)
    self.assertEqual(resp.text, 'Forbidden')

  def test_write_outside_base_path_should_fail(self):
    self.setUpRecipe({'allow-write': 'true'})
    server_base_url = self.startServer()

    # A file outside the server's root directory
    hack_path = os.path.join(self.install_dir, 'forbidden', 'hack.txt')
    hack_content = "You should not be able to write to hack.txt"

    self.write_should_fail(server_base_url, hack_path, hack_content)
    self.assertFalse(os.path.exists(os.path.dirname(hack_path)))

  def test_write(self):
    self.setUpRecipe({'allow-write': 'true'})
    server_base_url = self.startServer()

    # post with multipart/form-data encoding
    resp = requests.post(
        server_base_url,
        files={
            'path': 'hello-form-data.txt',
            'content': 'hello-form-data',
        },
    )
    self.assertEqual(resp.status_code, requests.codes.ok)
    self.assertEqual(resp.text, 'Content written to hello-form-data.txt')
    with open(
        os.path.join(self.base_path, 'hello-form-data.txt')) as f:
      self.assertEqual(f.read(), 'hello-form-data')

    self.assertIn('hello-form-data.txt', requests.get(server_base_url).text)
    self.assertEqual(
        requests.get(server_base_url + '/hello-form-data.txt').text, 'hello-form-data')

    # post as application/x-www-form-urlencoded
    resp = requests.post(
        server_base_url,
        data={
            'path': 'hello-form-urlencoded.txt',
            'content': 'hello-form-urlencoded',
        },
    )
    self.assertEqual(resp.status_code, requests.codes.ok)
    with open(
        os.path.join(self.base_path, 'hello-form-urlencoded.txt')) as f:
      self.assertEqual(f.read(), 'hello-form-urlencoded')

    self.assertIn('hello-form-urlencoded.txt', requests.get(server_base_url).text)
    self.assertEqual(resp.text, 'Content written to hello-form-urlencoded.txt')
    self.assertEqual(
        requests.get(server_base_url + '/hello-form-urlencoded.txt').text, 'hello-form-urlencoded')

    # incorrect paths are refused
    for path in '/hello.txt', '../hello.txt':
      resp = requests.post(
          server_base_url,
          files={
              'path': path,
              'content': b'hello',
          },
      )
      self.assertEqual(resp.status_code, requests.codes.forbidden)

  def test_readonly(self):
    self.setUpRecipe()

    indexpath = os.path.join(self.base_path, 'index.txt')
    indexcontent = "This file is served statically and readonly"
    with open(indexpath, 'w') as f:
      f.write(indexcontent)

    server_base_url = self.startServer()
    indexurl = os.path.join(server_base_url, 'index.txt')

    resp = requests.get(indexurl)
    self.assertEqual(resp.status_code, requests.codes.ok)
    self.assertEqual(resp.text, indexcontent)

    resp = requests.post(
        server_base_url,
        files={
            'path': 'index.txt',
            'content': 'Not readonly after all',
        },
    )
    self.assertEqual(resp.status_code, requests.codes.forbidden)
    with open(indexpath) as f:
      self.assertEqual(f.read(), indexcontent)

  def test_socketpath(self):
    socketpath = os.path.join(self.install_dir, 'http.sock')
    self.setUpRecipe({'socketpath': socketpath})
    self.assertEqual(socketpath, self.recipe.options['address'])
    self.startServer()

  def test_abstract(self):
    abstract = os.path.join(self.install_dir, 'abstract.http')
    self.setUpRecipe({'abstract': abstract})
    self.assertEqual('\0' + abstract, self.recipe.options['address'])
    self.startServer()

  def test_tls_self_signed(self):
    certfile = os.path.join(self.install_dir, 'cert.pem')
    with open(certfile, 'w') as f:
      f.write(CERTIFICATE_FOR_TEST)

    self.setUpRecipe({'cert-file': certfile})
    with warnings.catch_warnings():
      warnings.simplefilter("ignore") # suppress verify=False warning
      server_base_url = self.startServer()

    # Check self-signed certificate is not accepted without verify=False
    self.assertRaises(
      requests.exceptions.ConnectionError,
      requests.get,
      server_base_url
    )
