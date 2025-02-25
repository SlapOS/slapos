import os
import fnmatch
import subprocess

from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise


@implementer(interface.IPromise)
class RunPromise(GenericPromise):

  def __init__(self, config):
    """
      Called when initialising the promise before testing.
      Sets the configuration and the periodicity.
    """
    super(RunPromise, self).__init__(config)
    self.setPeriodicity(minute=2)


  def sense(self):
    """
      Called every time the promise is tested.
      Signals a positive or negative result.

      In this case, check whether the file exists.
    """
    cron_log_path = self.getConfig('cron_log')
    if not os.path.isfile(cron_log_path):
      self.logger.error("cron_log %s does not exist or is not a file", cron_log_path)

    target_string = "1"

    partition_path = self.getConfig('partition_path')[:-3]
    cron_service_name = self.getConfig('cron_name')
    cron_log_file = self.getConfig('log_file')
    print(cron_log_file)
    # Find the crond log like
    # .slappart2_crond-94787cb8beef266b357c15b8ee69f958.log

    # Walk through the directory and its subdirectories
    # for root, _, files in os.walk(partition_path):
    #   for filename in files:
    #     if fnmatch.fnmatch(filename, '*slappart*cron*.log'):
    #       crond_log_file = os.path.join(root, filename)
    #       break
    # print(crond_log_file)
    # Check the log file, but which line should be considered as failed one?
    print("0000000000000000000000")

    # When run the slapos node instance, slapos can not check the cron result immediately
    # because the cron service may need to wait the midnight to launch.
    print(cron_log_file)
    if not os.path.exists(cron_log_file):
      return
    print("1111111111111111111111111")

    try:
      with open(cron_log_file, "r") as file:
        log_content = file.read()
        if "0" not in log_content:
          self.logger.error(f"Cron service {cron_service_name} failed with the code: {log_content}")
        print(log_content)
    except FileNotFoundError:
      print(f"File not found: {cron_log_file}")
    except Exception as e:
      print(f"An error occurred: {str(e)}")

    error_line = self.find_error_in_file(cron_log_path, target_string)

    if error_line:
      self.logger.error(f"There is an error in the cron log: {error_line}")

  def find_error_in_file(self, file_path, target_string):
    try:
      found_line = None

      with open(file_path, "r") as file:
        for line in file:
          if target_string in line:
            found_line = line.strip()  # Remove leading/trailing whitespace
            break  # Stop searching once found

      return found_line

    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

  def test(self):
    """
      Called after sense() if the instance is still converging.
      Returns success or failure based on sense results.

      In this case, fail if the previous sensor result is negative.
    """
    return self._test(result_count=1, failure_amount=1)


  def anomaly(self):
    """
      Called after sense() if the instance has finished converging.
      Returns success or failure based on sense results.
      Failure signals the instance has diverged.

      In this case, fail if two out of the last three results are negative.
    """
    return self._anomaly(result_count=3, failure_amount=2)
