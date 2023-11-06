#!{{ python_path }}
import time
import json
import xmltodict
import sys
import re
import os
sys.path.append({{ repr(buildout_directory_path) }})
from ncclient_common import LopcommNetconfClient

if __name__ == '__main__':
    nc = LopcommNetconfClient(
        log_file="{{ log_file }}",
        supervision_reply_json_log_file="{{ supervision_reply_json_log_file }}"
    )
    try:
        netconf_check_file = '{{ is_netconf_connected }}'
        nc.connect("{{ netaddr.IPAddress(slap_configuration.get('tap-ipv6-gateway', '')) }}", 830, "oranuser", "oranpassword")

        supervision_subscription_rpc_xml = """
            <create-subscription xmlns="urn:ietf:params:xml:ns:netconf:notification:1.0">
                <stream>o-ran-supervision</stream>
            </create-subscription>
        """
        nc.logger.info("Subscription creating...")
        supervision_subscription_reply_xml = nc.custom_rpc_request(supervision_subscription_rpc_xml)

        if supervision_subscription_reply_xml:
            nc.logger.info("Subscription created")
            supervision_subscription_data = xmltodict.parse(supervision_subscription_reply_xml)
            nc.supervision_reply_json_logger.info('', extra={'data': json.dumps(supervision_subscription_data)})
            while True:
              supervision_watchdog_rpc_xml = """
                  <supervision-watchdog-reset xmlns="urn:o-ran:supervision:1.0">
                          <supervision-notification-interval>60</supervision-notification-interval>
                          <guard-timer-overhead>10</guard-timer-overhead>
                  </supervision-watchdog-reset>
              """
              nc.logger.info("NETCONF server replying...")
              supervision_watchdog_reply_xml = nc.custom_rpc_request(supervision_watchdog_rpc_xml)
              if supervision_watchdog_reply_xml:
                  if not os.path.exists(netconf_check_file):
                      open(netconf_check_file, "w").write('True')
                      nc.logger.info("NETCONF server replied")
                      
                      supervision_watchdog_data = xmltodict.parse(supervision_watchdog_reply_xml)
                      nc.supervision_reply_json_logger.info('', extra={'data': json.dumps(supervision_watchdog_data)})
                      # It must be the same interval as <supervision-notification-interval>
                      time.sleep(60)
                  else:
                      if os.path.exists(netconf_check_file):
                          os.remove(netconf_check_file)

        else:
          nc.logger.debug("Subscription failed.")

    except Exception as e:
        nc.logger.debug('Got exception, waiting 10 seconds before reconnecting...')
        nc.logger.debug(str(e))
        time.sleep(10)
    finally:
        nc.close()