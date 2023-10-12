#!{{ python_path }}
import time
import sys
sys.path.append({{ repr(buildout_directory_path) }})
from ncclient_common import LopcommNetconfClient

if __name__ == '__main__':
  nc = LopcommNetconfClient(
    log_file="{{ log_file }}",
    json_log_file="{{ json_log_file }}",
    cfg_json_log_file="{{ cfg_json_log_file }}",
    supervision_json_log_file="{{ supervision_json_log_file }}",
    ncsession_json_log_file="{{ ncsession_json_log_file }}",
    software_json_log_file="{{ software_json_log_file }}"
    )
  while True:
    try:
        # XXX temp -> reenable
        #nc.connect("{ { netaddr.IPAddress(slap_configuration.get('tap-ipv6-gateway', '')) } }", 830, "oranuser", "oranpassword")
        nc.connect("{{ netaddr.IPAddress('::1') }}", 830, "oranuser", "oranpassword")
        nc.subscribe()
        while True:
          nc.get_notification()
    except Exception as e:
        nc.logger.debug('Got exception, waiting 10 seconds before reconnecting...')
        nc.logger.debug(e)
        time.sleep(10)
    finally:
        nc.close()
