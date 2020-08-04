import os
import subprocess

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TransferDataTest(SlapOSInstanceTestCase):
  
  def create_embulk_config(self, config, data_in_file_name, data_out_path):
    config_string = "exec:\n max_threads: 1\n min_output_tasks: 1\n" + \
      "in:\n type: filename\n path_prefix: %s\n parser:\n  type: none-bin\n" + \
      "out:\n type: file\n path_prefix: %s\n file_ext: wen\n formatter:\n  type: single_value"
      
    config_string = config_string % (data_in_file_name, data_out_path)
    f = open(config,'w')
    print >> f,config_string
    f.close()
  
  def test_transfer_data(self):
    pwd = os.getcwd()
    config = pwd + "/config.yml"
    data_in_file_name = pwd + "/data-in.wen"
    data_out_path = pwd + "/data_out"
    
    data_in = "It works"
    data_in_file = open(data_in_file_name, 'w')
    data_in_file.write(data_in)
    data_in_file.close()
    
    self.create_embulk_config(config, data_in_file_name, data_out_path)
    subprocess.call(['{{ java_location }}/bin/java', '-jar', '{{ embulk_location }}/embulk.jar', 
      'run', config, '-b', '{{ embulkPlugins_location }}/plugins'])
    
    data_out_path = data_out_path + "000.00.wen"
    data_out_file = open(data_out_path, 'rb')
    data_out = data_out_file.read()
    data_out_file.close()

    self.assertEqual(data_in, base64.b64decode(data_out))
    
    os.remove(config)
    os.remove(data_in_file_name)
    os.remove(data_out_path)
    
                    