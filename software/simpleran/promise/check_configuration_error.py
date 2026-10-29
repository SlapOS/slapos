from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

import hashlib, os

def hash_file_list(file_list):
    h = hashlib.sha256()
    for path in file_list:
        with open(path, 'rb') as f:
            h.update(f.read())
    return h.hexdigest()

@implementer(interface.IPromise)
class RunPromise(GenericPromise):
    def __init__(self, config):
        super(RunPromise, self).__init__(config)
        self.setPeriodicity(1)
        self.allowBang(False)
    def sense(self):
        error = self.getConfig('error')
        dry_config_file_list = self.getConfig('dry-config-file-list').split(' ')
        running_config_directory = self.getConfig('running-config-directory')

        if error:
            self.logger.error("Invalid parameters: %s", error)
            return

        # Promises are generated before amarisoft-wrapper.py runs, so instead of checking Amarisoft
        # stderr from dry run we need to check if running config files match the generated ones
        running_config_file_list = []
        for path in dry_config_file_list:
            filename = os.path.basename(path)
            running_config_file_list.append(os.path.join(running_config_directory, filename))

        running_config_hash = hash_file_list(running_config_file_list)
        dry_config_hash     = hash_file_list(dry_config_file_list)

        if running_config_hash != dry_config_hash:
            self.logger.error(f"Amarisoft dry run failed, please check ERROR.amarisoft connection parameter " \
                               "or Amarisoft stdout log")
        self.logger.info("No errors during parameter validation")

    def test(self):
        return self._test(result_count=1, failure_amount=1)
    def anomaly(self):
        return self._anomaly(result_count=1, failure_amount=1)

