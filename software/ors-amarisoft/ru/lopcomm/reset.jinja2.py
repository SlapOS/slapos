#!{{ python_path }}
import time
import sys
sys.path.append({{ repr(buildout_directory_path) }})
from ncclient_common import LopcommNetconfClient

if __name__ == '__main__':
  nc = LopcommNetconfClient(log_file="{{ log_file }}")
  while True:
      try:
          nc.connect("{{ netaddr.IPAddress(slap_configuration.get('tap-ipv6-gateway', '')) }}", 830, "oranuser", "oranpassword")
          nc.nc.reset_device()
          break
      except Exception as e:
          nc.logger.debug('Got exception, waiting 10 seconds before reconnecting...')
          nc.logger.debug(e)
          time.sleep(10)
      finally:
          nc.close()
