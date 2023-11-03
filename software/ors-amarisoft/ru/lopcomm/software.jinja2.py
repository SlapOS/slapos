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
    software_reply_json_log_file="{{ software_reply_json_log_file }}"
    )
  while True:
      try:
          firmware_check_file= os.path.join('{{etc_path}}','is_firmware_updated')
          nc.connect("{{ netaddr.IPAddress(slap_configuration.get('tap-ipv6-gateway', '')) }}", 830, "oranuser", "oranpassword")
          # Fetch software inventory

          inventory_vars = nc.get_inventory()

          nonrunning_slot_name = inventory_vars["nonrunning_slot_name"]
          running_slot_name = inventory_vars["running_slot_name"]
          active_nonrunning_slot_name = inventory_vars["active_nonrunning_slot_name"]
          nonrunning_slot_name_build_version = inventory_vars["nonrunning_slot_name_build_version"]
          running_slot_name_build_version = inventory_vars["running_slot_name_build_version"]

          if running_slot_name and nonrunning_slot_name:
              if running_slot_name:
                  nc.logger.info("One slot is running and one is non-running. Proceeding...")
                  if running_slot_name_build_version in "{{firmware_name}}":
                      if not os.path.exists(firmware_check_file):
                        open(firmware_check_file, "w").write('True')
                      nc.logger.info("Running slot's build-version %s is already updated. Skipping install." % running_slot_name_build_version)
                  else:
                      if os.path.exists(firmware_check_file):
                        os.remove(firmware_check_file)
                      nc.logger.info("Current build version: %s" % running_slot_name_build_version)
                      user_authorized_key ="""{{ slapparameter_dict.get('user-authorized-key', '') }}"""
                      match = re.match(r'ssh-rsa ([^\s]+)', user_authorized_key)
                      if match:
                          extracted_key = match.group(1)
                      else:
                          nc.logger.info("No valid key found in user authorized key.")
                      download_rpc_xml = f"""
                          <software-download xmlns="urn:o-ran:software-management:1.0">
                              <remote-file-path>{{remote_file_path}}</remote-file-path>
                              <server>
                                      <keys>
                                      <algorithm xmlns:ct="urn:ietf:params:xml:ns:yang:ietf-crypto-types">1024</algorithm>
                                      <public-key>{extracted_key}</public-key>
                                      </keys>
                              </server>
                          </software-download>
                      """
                      download_reply_xml = nc.custom_rpc_request(download_rpc_xml)
                      nc.logger.info("Downloading software...")
                      time.sleep(60)
                      if download_reply_xml:
                          nc.logger.info("Download proceed.")
                          download_data = xmltodict.parse(download_reply_xml)
                          nc.software_reply_json_logger.info('', extra={'data': json.dumps(download_data)})

                      install_rpc_xml = f"""
                          <software-install xmlns="urn:o-ran:software-management:1.0">
                              <slot-name>{nonrunning_slot_name}</slot-name>
                              <file-names>{{firmware_name}}</file-names>
                          </software-install>
                      """
                      install_reply_xml = nc.custom_rpc_request(install_rpc_xml)
                      nc.logger.info("Installing software...")
                      time.sleep(60)
                      if install_reply_xml:
                          nc.logger.info("Installation proceed.")
                          install_data = xmltodict.parse(install_reply_xml)
                          nc.software_reply_json_logger.info('', extra={'data': json.dumps(install_data)})

                      if nonrunning_slot_name_build_version in "{{firmware_name}}":
                          activate_rpc_xml = f"""
                              <software-activate xmlns="urn:o-ran:software-management:1.0">
                                  <slot-name>{nonrunning_slot_name}</slot-name>
                              </software-activate>
                          """
                          activate_reply_xml = nc.custom_rpc_request(activate_rpc_xml)
                          nc.logger.info("Activating software...")
                          time.sleep(60)
                          if activate_reply_xml:
                              nc.logger.info("Activation proceed.")
                              activate_data = xmltodict.parse(activate_reply_xml)
                              nc.software_reply_json_logger.info('', extra={'data': json.dumps(activate_data)})

                      nc.get_inventory()
                      if nonrunning_slot_name_build_version in "{{firmware_name}}" and active_nonrunning_slot_name:
                          nc.logger.info("Active non-running slot has the updated build version. Resetting device.")
                          nc.reset_device()
          break
      except Exception as e:
          nc.logger.debug('Got exception, waiting 10 seconds before reconnecting...')
          nc.logger.debug(str(e))
          time.sleep(10)
      finally:
          nc.close()
