#!{{ python_path }}
import os
import time
import sys
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

if __name__ == '__main__':
    nc = LopcommNetconfClient(log_file="{{ log_file }}")

    while True:
        src = "{{ cu_config_template }}"
        dst = "{{ cu_config_template }}.old"

        # Send standard configuration initially
        send_config(nc, ["{{ CreateProcessingEle_template }}", "{{ cu_config_template }}"])

        if os.path.exists(dst):
            with open(src, 'r') as src_file:
                src_content = src_file.read()
            with open(dst, 'r') as dst_file:
                dst_content = dst_file.read()

            if src_content == dst_content:
                nc.logger.info("No changes on cu_config.xml, exit")
                sys.exit(0)
            else:
                nc.logger.debug("Content of src and dst are different")
                nc.logger.debug("src content: \n%s", src_content)
                nc.logger.debug("dst content: \n%s", dst_content)

                send_config(nc, ["{{ CreateProcessingEle_template }}", "{{ cu_inactive_config_template }}", "{{ cu_config_template }}"])
        else:
            # If dst does not exist, copy src to dst
            shutil.copyfile(src, dst)
            nc.logger.info("Initial copy of src to dst completed.")
