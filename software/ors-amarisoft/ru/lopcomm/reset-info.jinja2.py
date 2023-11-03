#!{{ python_path }}
import paramiko
import logging
from logging.handlers import RotatingFileHandler

def get_uptime(hostname, username, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(hostname, username=username, password=password)
        stdin, stdout, stderr = client.exec_command('uptime')
        uptime_output = stdout.read().decode()
        return uptime_output

    except Exception as e:
        logger.info(f"Error: {e}")
    finally:
        client.close()

# Usage
hostname = "{{ netaddr.IPAddress(slap_configuration.get('tap-ipv6-gateway', '')) }}"
username = "oranuser"
password = "oranpassword"

# Initialize logger
log_file = "{{ log_file }}"
logger = logging.getLogger('logger')
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(log_file, maxBytes=30000, backupCount=2)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

if {{ testing }}:
  pass
else:
  rrh_uptime = get_uptime(hostname, username, password)
  logger.info(f"Uptime from RRH: {rrh_uptime}")
