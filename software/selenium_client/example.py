"""Run the web application through remote selenium browsers."""

import argparse
import itertools
import logging
import os
import traceback
from datetime import datetime
from multiprocessing import Queue
from threading import Thread
from urllib3 import PoolManager
from urllib3.exceptions import ProtocolError

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.remote_connection import RemoteConnection
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SELENIUM_INSTANCE_DICT= {
#  'https://selenium:PASSWORD@[IPV6]:9443/wd/hub': 1,
}

TIMEOUT = 30
NUMBER_OF_DRONES = 1
GRANULARITY = 4
GAME_INPUT_DICT = {
  'simulation_speed': '100000',
  'number_of_drones': str(NUMBER_OF_DRONES),
}
DRONE_INPUT_DICT = {
  "maxDeceleration": (1, 15),
  "speedFactor": (0.5, 2.5)
}

parser = argparse.ArgumentParser(
  prog='run_web_application',
  description='use selenium to run a web application and collect the logged results',
)
parser.add_argument(
  '-d', '--directory', type=str, default='.', help='location to store results')
parser.add_argument(
  '-u', '--url', type=str, default='https://dronesimulator.app.officejs.com/', help='simulator url')
args = parser.parse_args()
os.makedirs(args.directory, exist_ok=True)

def createDriver(options, selenium_url):
  # XXX we are using a self signed certificate, but selenium 3.141.0 does
  # not expose API to ignore certificate verification
  executor = RemoteConnection(selenium_url, keep_alive=True)
  executor._conn = PoolManager(cert_reqs='CERT_NONE', ca_certs=None)
  return webdriver.Remote(
    command_executor=executor,
    desired_capabilities=options.to_capabilities(),
    keep_alive=True,
  )

def chromeOptions():
  options = webdriver.ChromeOptions()
  options.add_argument('--headless=new')
  options.browser_version = '120'
  return options

def downloadLogs(driver, combination, result_dir):
  """Collect results from application run"""
  for i in range(NUMBER_OF_DRONES):
    id_s = "log_result_" + str(i)
    result_log = driver.find_element(
      By.XPATH, '//textarea[@id="log_result_%s"]' % i)
    with open(
      os.path.join(
        result_dir,
        'simulation_log_%s.log' % '_'.join(('%s_%s' % (k, v) for k, v in zip(DRONE_INPUT_DICT, combination)),
      )
    ), 'w') as f:
      f.write(result_log.get_attribute('value'))

def selenium_task(driver, app_url, combination, data_queue, error_logger):
  try:
    try:
      driver.set_window_size(1000, 4080)
      driver.get(app_url)

      WebDriverWait(driver, TIMEOUT).until(
        EC.presence_of_element_located((By.XPATH, '//iframe'))
      )

      for key, value in GAME_INPUT_DICT.items():
        driver.execute_script(
          'arguments[0].value = ' + value,
          driver.find_element(By.ID, key),
        )
      for i, key in enumerate(DRONE_INPUT_DICT):
        driver.execute_script(
          'arguments[0].value = ' + str(combination[i]),
          driver.find_element(By.ID, key),
        )

      driver.find_element(
        By.XPATH, '//input[@type="submit" and @name="action_run"]').click()
      WebDriverWait(driver, TIMEOUT).until(
        EC.presence_of_element_located((By.XPATH, '//div[@class="container"]//a[contains(text(), "Download Simulation LOG")]'))
      )
      downloadLogs(driver, combination, args.directory)
      if not data_queue.empty():
        driver.refresh()
    except (TimeoutException, WebDriverException):
      driver.refresh()
      raise
    except ProtocolError:
      driver = createDriver(chromeOptions(), driver.command_executor._url)
      raise
  except Exception as e:
    error_logger.error(driver.command_executor._url)
    error_logger.error(e)
    error_logger.error(traceback.format_exc())
    data_queue.put(combination)

def selenium_queue_listener(data_queue, worker_queue, selenium_worker_list, app_url, combination_nb, error_logger):
  while not data_queue.empty():
    current_data = data_queue.get()
    worker_id = worker_queue.get()
    selenium_task(selenium_worker_list[worker_id], app_url, current_data, data_queue, error_logger)
    worker_queue.put(worker_id)
    update_progress((combination_nb - data_queue.qsize()) / combination_nb)
  return

def values_in_range(start, end, n):
  if n == 1:
    return [start]
  d = (end - start) / (n - 1)
  return [start + i*d for i in range(n)]

def update_progress(progress):
  bar_length = 20
  if isinstance(progress, int):
    progress = float(progress)
  if not isinstance(progress, float):
    progress = 0
  if progress < 0:
    progress = 0
  if progress >= 1:
    progress = 1

  block = int(round(bar_length * progress))
  text = "Progress: [{0}] {1:.1f}%".format( "#" * block + "-" * (bar_length - block), progress * 100)
  print(text, end='\r')

##### MAIN #####
worker_queue = Queue()
selenium_worker_list = []
if not SELENIUM_INSTANCE_DICT:
  raise ValueError('SELENIUM_INSTANCE_DICT is empty')
print('Creating web drivers ' + datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
for i, url in enumerate(
  (url for url, slot_quantity in SELENIUM_INSTANCE_DICT.items() for _ in range(slot_quantity))
):
  selenium_worker_list.append(createDriver(chromeOptions(), url))
  worker_queue.put(i)

drone_input_value_tuple = (values_in_range(start, end, GRANULARITY) for start, end in DRONE_INPUT_DICT.values())
combination_list = [combination for combination in itertools.product(*drone_input_value_tuple)]
combination_nb = len(combination_list)
print('Total combinations: ' + str(combination_nb))
selenium_data_queue = Queue()
for d in combination_list:
  selenium_data_queue.put(d)

creation_time = datetime.now()
print('Starting selenium background processes ' + creation_time.strftime('%d/%m/%Y %H:%M:%S'))
error_logger = logging.getLogger(__name__)
logging.basicConfig(filename='error.log')
selenium_processes = [
  Thread(target=selenium_queue_listener,
         args=(selenium_data_queue, worker_queue, selenium_worker_list, args.url, combination_nb, error_logger))
  for _ in range(len(selenium_worker_list))
]
update_progress(0)
for p in selenium_processes:
  p.daemon = True
  p.start()
for p in selenium_processes:
  p.join()
elapsed_time = datetime.now() - creation_time
print('\nTotal time for runs: %s seconds.' % elapsed_time.seconds)

for b in selenium_worker_list:
  try:
    b.quit()
  except WebDriverException as e:
    error_logger.error(e)
    error_logger.error(traceback.format_exc())
