#!{{ python_path }}
import os
import time
import sys
import shutil
sys.path.append({{ repr(buildout_directory_path) }})
from ncclient_common import LopcommNetconfClient

def send_config(nc, templates):
    try:
        nc.connect("{{ netaddr.IPAddress(vtap.gateway) }}", 830, "oranuser", "oranpassword")
        nc.edit_config(templates)
        nc.logger.info("RU config sent")
    except Exception as e:
        nc.logger.debug('Got exception, waiting 10 seconds before reconnecting...')
        nc.logger.debug(e)
        time.sleep(10)
    finally:
        nc.close()

def check_config_changes(src, dst, nc):
    """Check if configuration has changed and handle accordingly"""
    if not os.path.exists(dst):
        # Initial setup
        shutil.copyfile(src, dst)
        nc.logger.info("Initial copy of src to dst completed.")
        return False

    with open(src, 'r') as src_file, open(dst, 'r') as dst_file:
        src_content = src_file.read()
        dst_content = dst_file.read()

    if src_content == dst_content:
        nc.logger.info("No changes on cu_config.xml")
        return False
    
    nc.logger.debug("Content of src and dst are different")
    nc.logger.debug("src content: \n%s", src_content)
    nc.logger.debug("dst content: \n%s", dst_content)
    return True

def main():
    nc = LopcommNetconfClient(log_file="{{ log_file }}")
    last_deactivation_date = 0

    src = "{{ cu_config_template }}"
    dst = "{{ cu_config_template }}.old"

    while True:
        # Send standard configuration initially
        send_config(nc, ["{{ CreateProcessingEle_template }}", "{{ cu_config_template }}"])

        date_str = open("{{ enb_start_date }}").read().strip()
        enb_start_date = time.mktime(time.strptime(date_str, "%Y%m%d.%H:%M:%S"))

        nc.logger.info("Current enb_start_date: %s", enb_start_date)
        nc.logger.info("Current last_deactivation_date: %s", last_deactivation_date)
        
        # Check if deactivation is needed
        if last_deactivation_date < enb_start_date:
            nc.logger.info("Deactivation needed - enb_start_date: %s", enb_start_date)
            last_deactivation_date = time.time()
            nc.logger.info("Setting new deactivation_date: %s", last_deactivation_date)
            send_config(nc, ["{{ CreateProcessingEle_template }}", 
                           "{{ cu_inactive_config_template }}", 
                           "{{ cu_config_template }}"])
        
        # Check for configuration changes
        if check_config_changes(src, dst, nc):
            send_config(nc, ["{{ CreateProcessingEle_template }}", 
                           "{{ cu_inactive_config_template }}", 
                           "{{ cu_config_template }}"])
            shutil.copyfile(src, dst)  # Update the reference config
        
        # Add a sleep to prevent tight loop
        time.sleep(30) 

if __name__ == '__main__':
    main()