
from multiprocessing import Process, active_children, cpu_count, Pipe
import subprocess
import os
import signal
import sys
import time

FIB_N = 100
DEFAULT_TIME = 60
try:
    DEFAULT_CPU = cpu_count()
except NotImplementedError:
    DEFAULT_CPU = 1

def collectComputerTemperature(sensor_bin="sensors"):
  cmd = ["%s -u" % sensor_bin]
  
  sp = subprocess.Popen(cmd, stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE, shell=True)
  
  stdout, stderr = sp.communicate()
  
  sensor_output_list = stdout.splitlines()
  adapter_name = ""
  
  sensor_temperature_list = []
  for line_number in range(len(sensor_output_list)):
    found_sensor = None
    stripped_line = sensor_output_list[line_number].strip()
    if stripped_line.startswith("Adapter:"):
      adapter_name = sensor_output_list[line_number-1]
   
    elif stripped_line.startswith("temp") and "_input" in stripped_line:
      temperature = sensor_output_list[line_number].split()[-1] 
      found_sensor = ["%s %s" % (adapter_name, sensor_output_list[line_number-1]), float(temperature)]
  
    if found_sensor is not None:
      critical = '1000'
      maximal = '1000'
      for next_line in sensor_output_list[line_number+1:line_number+3]:
        stripped_next_line = next_line.strip()  
        if stripped_next_line.startswith("temp") and "_max" in stripped_next_line:
          maximal = stripped_next_line.split()[-1]
        elif stripped_next_line.startswith("temp") and "_crit" in stripped_next_line:
          critical = stripped_next_line.split()[-1]
  
      found_sensor.extend([float(maximal), float(critical)]) 
      found_sensor.append(checkAlarm(float(temperature), float(maximal), float(critical)))
      sensor_temperature_list.append(found_sensor)
  return sensor_temperature_list

def checkAlarm(temperature, maximal, critical):
  """
    Returns :
      O if the temperature is below the maximal limit.
      1 if the temperature is above the maximal limit.
      2 if the temperature is above the crical limit.
  """ 
  alarm = 0
  if temperature >= maximal:
    alarm += 1

  if temperature >= critical:
    alarm += 1

  return alarm

def loop(connection):
  connection.send(os.getpid())
  connection.close()
  while True:
    fib(FIB_N)

def fib(n):
  if n < 2:
    return 1
  else:
    return fib(n - 1) + fib(n - 2)

def sigint_handler(signum, frame):
    procs = active_children()
    for p in procs:
        p.terminate()
    os._exit(1)

def launchTemperatureTest(sensor_id, sensor_bin="sensors", timeout=600, interval=30):

  signal.signal(signal.SIGINT, sigint_handler)

  def getTemperatureForSensor(s_id):
    for collected_temperature in collectComputerTemperature(sensor_bin):
      if collected_temperature[0] == sensor_id:
        return collected_temperature[1], collected_temperature[4]

    return None, None

  process_list = []
  process_connection_list = []

  begin_time = time.time()
  initial_temperature, alarm = getTemperatureForSensor(sensor_id)

  if initial_temperature is None:
    return

  if alarm > 0:
    # Skip to test if temperature is too high, because we cannot 
    # measure appropriatetly.
    return

  candidate_temperature = initial_temperature

  for i in range(DEFAULT_CPU):
    parent_connection, child_connection = Pipe()
    process = Process(target=loop, args=(child_connection,))
    process.start()
    process_list.append(process)
    process_connection_list.append(parent_connection)

  for connection in process_connection_list:
    try:
      print connection.recv()
    except EOFError:
      continue

  time.sleep(interval)
  current_temperature = getTemperatureForSensor(sensor_id)
  
  while current_temperature > candidate_temperature:
    candidate_temperature = current_temperature
    time.sleep(interval)
    current_temperature = getTemperatureForSensor(sensor_id)

  for process in process_list:
    process.terminate()

  return initial_temperature, current_temperature, time.time() - begin_time


