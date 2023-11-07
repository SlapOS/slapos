#!{{ python_path }}
import time
import sys
sys.path.append({{ repr(buildout_directory_path) }})
from ncclient_common import LopcommNetconfClient

if __name__ == '__main__':
    nc = LopcommNetconfClient(log_file="{{ log_file }}")
    try:
        nc.connect("{{ netaddr.IPAddress(vtap.gateway) }}", 830, "oranuser", "oranpassword")
        nc.reset_device()
        nc.logger.info("Device reset successful.")
    except Exception as e:
        nc.logger.debug('Got exception while resetting...')
        nc.logger.debug(e)
    finally:
        nc.close()
