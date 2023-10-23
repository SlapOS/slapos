#!{{ python_path }}
import time
import sys
sys.path.append({{ repr(buildout_directory_path) }})
from ncclient_common import LopcommNetconfClient

if __name__ == '__main__':
  nc = LopcommNetconfClient(log_file="{{ log_file }}")
  while True:
      try:
          nc.connect("{{ netaddr.IPAddress(vtap.gateway) }}", 830, "oranuser", "oranpassword")
          # XXX CreateProcessingEle should be also RU-specific ?
          nc.edit_config(["{{ ru_lopcomm_CreateProcessingEle_template }}", "{{ cu_config_template }}"])
          break
      except Exception as e:
          nc.logger.debug('Got exception, waiting 10 seconds before reconnecting...')
          nc.logger.debug(e)
          time.sleep(10)
      finally:
          nc.close()
