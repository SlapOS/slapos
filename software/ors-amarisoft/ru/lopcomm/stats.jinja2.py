#!{{ python_path }}
import time
import sys
import os
import threading

sys.path.append({{ repr(buildout_directory_path) }})
from ncclient_common import LopcommNetconfClient

def get_notification_continuously(nc):
    while True:
        nc.get_notification()

def run_supervision_reset_continuously(nc):
    netconf_check_file = '{{ is_netconf_connected }}'
    interval = 60
    margin   = 10
    while True:
        t0 = time.time()
        nc.supervision_reset(interval, margin)
        with open(netconf_check_file, "w") as f:
          f.write('True')
        t1 = time.time()
        time.sleep(interval - (t1-t0))

if __name__ == '__main__':
    nc = LopcommNetconfClient(
        log_file="{{ log_file }}",
        json_log_file="{{ json_log_file }}",
        cfg_json_log_file="{{ cfg_json_log_file }}",
        supervision_json_log_file="{{ supervision_json_log_file }}",
        ncsession_json_log_file="{{ ncsession_json_log_file }}",
        software_json_log_file="{{ software_json_log_file }}",
        supervision_reply_json_log_file="{{ supervision_reply_json_log_file }}"
    )
    while True:
        try:

            nc.connect("{{ netaddr.IPAddress(slap_configuration.get('tap-ipv6-gateway', '')) }}", 830, "oranuser", "oranpassword")
            nc.subscribe()

            # Create threads for continuous execution of both tasks
            notification_thread = threading.Thread(target=get_notification_continuously, args=(nc,))
            supervision_thread = threading.Thread(target=run_supervision_reset_continuously, args=(nc,))

            # Start the threads
            notification_thread.start()
            supervision_thread.start()

            # Wait for threads to complete (this will not happen as they run indefinitely)
            notification_thread.join()
            supervision_thread.join()

        except Exception as e:
            nc.logger.debug('Got exception, waiting 10 seconds before reconnecting...')
            nc.logger.debug(e)
            time.sleep(10)
        finally:
            nc.close()
