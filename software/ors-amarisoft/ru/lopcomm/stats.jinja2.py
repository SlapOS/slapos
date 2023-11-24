#!{{ python_path }}
import time
import sys
import os
import threading

sys.path.append({{ repr(buildout_directory_path) }})
from ncclient_common import LopcommNetconfClient

# Shared variable to indicate error occurred
error_occurred = False
lock = threading.Lock()

def get_notification_continuously(nc):
    global error_occurred
    try:
        while not error_occurred:
            nc.get_notification()
            pass
    except Exception as e:
        with lock:
            error_occurred = True
            nc.logger.error(f'Error in get_notification_continuously: {e}')

# supervision watchdog keeps on
def run_supervision_reset_continuously(nc):
    global error_occurred
    netconf_check_file = '{{ is_netconf_connected }}'
    interval = 60
    margin   = 10
    try:
        while not error_occurred:
            t0 = time.time()
            replied = nc.supervision_reset(interval, margin)
            if replied:
                with open(netconf_check_file, "w") as f:
                    f.write('')
            elif os.path.exists(netconf_check_file):
                os.remove(netconf_check_file)

            t1 = time.time()
            time.sleep(interval - (t1 - t0))
    except Exception as e:
        with lock:
            error_occurred = True
            nc.logger.error(f'Error in run_supervision_reset_continuously: {e}')

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
    threads = []

    try:
        nc.connect("{{ netaddr.IPAddress(vtap.gateway) }}", 830, "oranuser", "oranpassword")
        nc.subscribe()

        notification_thread = threading.Thread(target=get_notification_continuously, args=(nc,))
        supervision_thread = threading.Thread(target=run_supervision_reset_continuously, args=(nc,))

        threads.append(notification_thread)
        threads.append(supervision_thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

    except Exception as e:
        nc.logger.debug('Got exception, waiting 10 seconds before reconnecting...')
        nc.logger.debug(e)
        time.sleep(10)
    finally:
        nc.close()
