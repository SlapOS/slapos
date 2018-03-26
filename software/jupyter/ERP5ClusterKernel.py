from ipykernel.kernelbase import Kernel
from ipykernel.kernelapp import IPKernelApp
import cPickle
import requests
import uritemplate
import sys
import time

REQUEST_TIMEOUT = 60
PROCESS_TIMEOUT = 600

erp5_url = None
if len(sys.argv) > 1:
    erp5_url = "%s/erp5/web_site_module/hateoas/" % (sys.argv[1],)

class LoggedRequests(object):
  """Requests with login

  Also avoid verification of SSL certificates"""
  def __init__(self, user, password):
    self.auth = (user, password)

  def get(self, *args, **kwargs):
    return requests.get(
      auth=self.auth, timeout=REQUEST_TIMEOUT, verify=False, *args, **kwargs)

  def post(self, *args, **kwargs):
    return requests.post(
      auth=self.auth, timeout=REQUEST_TIMEOUT, verify=False, *args, **kwargs)

class MagicInfo:
  """
  Magics definition structure.
  Initializes a new MagicInfo class with specific paramters to identify a magic.
  """
  def __init__(self, magic_name):
    self.magic_name = magic_name

MAGICS = {
  'erp5_user': MagicInfo('erp5_user'),
  'erp5_password': MagicInfo('erp5_password'),
  'erp5_url': MagicInfo('erp5_url'),
  }

class ERP5ClusterKernel(Kernel):
  """
  Jupyter Kernel class to interact with erp5 backend for code from frontend.
  To use this kernel with erp5, user need to install 'erp5_data_notebook' bt5
  Also, handlers(aka magics) starting with '%' are predefined.

  Each request to erp5 for code execution requires erp5_user, erp5_password.
  """

  implementation = 'ERP5 Cluster'
  implementation_version = '1.0'
  language_info = {'mimetype': 'text/x-python', 'name':'python'}
  banner = "ERP5 Cluster integration with jupyter notebook"

  def __init__(self, *args, **kwargs):
    super(ERP5ClusterKernel, self).__init__(*args, **kwargs)
    self.erp5_user = None
    self.erp5_password = None
    self.erp5_url = erp5_url
    self.erp5_data_notebook = None
    self.cluster_data_notebook_uri = None
    self.logged_requests = None
    self.traverse_url = None

  def display_response(self, response=None):
    """
      Dispays the stream message response to jupyter frontend.
    """
    if response:
      stream_content = {'name': 'stdout', 'text': response}
      self.send_response(self.iopub_socket, 'stream', stream_content)

  def set_magic_attribute(self, magic_info=None, code=None):
    """
      Set attribute for magic which are necessary for making requests to erp5.
      Catch errors and display message. Since user is in contact with jupyter
      frontend, so its better to catch exceptions and dispaly messages than to
      let them fail in backend and stuck the kernel.
      For a making a request to erp5, we need -
      erp5_url, erp5_user, erp5_password
    """
    # Set attributes only for magic who do have any varible to set value to
    if magic_info.magic_name:
      try:
        # Get the magic value recived via code from frontend
        magic_value = code.split()[1]
        # Set magic_value to the required attribute
        required_attributes = ['erp5_password', 'erp5_user', 'erp5_url']
        missing_attributes = []
        for attribute in required_attributes:
          if not getattr(self, attribute):
            missing_attributes.append(attribute)

        if missing_attributes != []:
          response = "You still haven't entered all required magics."
        setattr(self, magic_info.magic_name , magic_value)
        if magic_info.magic_name != 'erp5_password':
          response = 'Your %s is %s. '%(magic_info.magic_name, magic_value)
        else:
          response = "Password in %s set." % (magic_info.magic_name,)

      # Catch exception while setting attribute and set message in response
      except AttributeError:
        response = 'Please enter %s magic value'%magic_info.magic_name

      # Catch IndexError while getting magic_value and set message in response object
      except IndexError:
        response = 'Empty value for %s magic'%magic_info.magic_name

      # Catch all other exceptions and set error_message in response object
      # XXX: Might not be best way, but its better to display error to the user
      # via notebook frontend than to fail in backend and stuck the Kernel without
      # any failure message to user.
      except Exception as e:
        response = str(e)

      # Display the message/response from this fucntion before moving forward so
      # as to keep track of the status
      if response != "":
        self.display_response(response=response + '\n')

  def check_required_attributes(self):
    """
      Check if the required attributes for making a request are already set or not.
    """
    required_attributes  = ['erp5_user', 'erp5_password', 'erp5_url']
    missing_attributes = []

    # Loop to check if the required attributes are set
    for attribute in required_attributes:
      if not getattr(self, attribute):
        missing_attributes.append(attribute)

    if missing_attributes:
      self.display_response(
        response='''You have these required magics remaining: %s. \n''' % (
        ', '.join(missing_attributes)))

    return missing_attributes

  def process_magic(self, code):
    # No need to try-catch here as its already been taken that the code
    # starts-with '%', so we'll get magic_name, no matter what be after '%'
    magic_name = code.split()[0][1:]
    magics_name_list = [magic.magic_name for magic in MAGICS.values()]

    # Check validation of magic
    if magic_name and magic_name in magics_name_list:

      # Get MagicInfo object related to the magic
      magic_info = MAGICS.get(magic_name)

      # Function call to set the required magics
      self.set_magic_attribute(magic_info=magic_info, code=code)

      # Call to check if the required_attributes are set
      missing = self.check_required_attributes()

      if not missing:
        self.display_response(
          'You have entered all required magics. You may now use your notebook.\n')

  def process_code(self, code):
    status = 'ok'

    # fetch the URL
    self.logged_requests = LoggedRequests(self.erp5_user, self.erp5_password)
    if self.cluster_data_notebook_uri is None:
      site = self.logged_requests.get(self.erp5_url)
      if site.status_code != 200:
        status = 'error'
        if site.status_code == 401:
          self.display_response('Login error: erp5_user and/or erp5_password are incorrect')
        else:
          self.display_response(site.text)
        return status
      site_json = site.json()
      self.traverse_url = site_json['_links']['traverse']['href']
      cluster_data_notebook_result = self.logged_requests.post(
        site_json['_actions']['add']['href'],
        data=dict(
          portal_type='Cluster Data Notebook',
          parent_relative_url='cluster_data_notebook_module'))
      if cluster_data_notebook_result.status_code != 201:
        status = 'error'
        if cluster_data_notebook_result.status_code == 401:
          self.display_response('Login error: erp5_user and/or erp5_password are incorrect')
        else:
          self.display_response(r.text)
        return status
      self.cluster_data_notebook_uri = cluster_data_notebook_result.headers['X-Location']

    cluster_data_notebook_url = uritemplate.URITemplate(self.traverse_url).expand(
      relative_url=self.cluster_data_notebook_uri.split(':')[3])

    cluster_data_notebook = self.logged_requests.get(cluster_data_notebook_url)
    post_execution_url = cluster_data_notebook.json()['_links']['action_object_jio_fast_input']['href']
    post_execution = self.logged_requests.get(post_execution_url)
    post_execution_form = post_execution.json()['_embedded']['_view']
    data = dict(
      dialog_method=post_execution_form['_actions']['put']['action'],
      dialog_id=post_execution_form['dialog_id']['default'],
      code=code
    )

    executor = self.logged_requests.post(
      post_execution_form['_actions']['put']['href'],
      data=data)

    # XXX: Server side bad
    executed_relative_url = executor.text

    executed_url = uritemplate.URITemplate(
      self.traverse_url).expand(relative_url=executed_relative_url)
    executed_view_url = [q for q in self.logged_requests.get(executed_url).json()['_links']['view'] if q['name'] == 'view'][0]['href']

    t = time.time()
    while True:
      executed_view = self.logged_requests.get(executed_view_url).json()
      state = executed_view['_embedded']['_view']['your_state']['default']
      if state == 'Ready':
        status = 'ok'
        self.display_response(executed_view['_embedded']['_view']['my_result']['default'])
        break
      if state == 'Error':
        status = 'error'
        self.display_response(executed_view['_embedded']['_view']['my_result']['default'])
        break
      if time.time() - t > PROCESS_TIMEOUT:
        status = 'error'
        self.display_response('Timeout after %is' % (PROCESS_TIMEOUT,))
        break
      time.sleep(0.5)
    return status

  def do_execute(self, code, silent, store_history=True, user_expressions=None,
                  allow_stdin=False):
    """
      Validate magic and call functions to make request to erp5 backend where
      the code is being executed and response is sent back which is then sent
      to jupyter frontend.
    """
    # By default, take the status of response as 'ok' so as show the responses
    # for erp5_url and erp5_user on notebook frontend as successful response.
    status = 'ok'
    # Remove spaces and newlines from both ends of code
    code = code.strip()

    extra_data_list = []
    print_result = {}
    displayhook_result = {}

    if code.startswith('%'):
      self.process_magic(code)
    else:
      # check that all required magics are set
      if self.check_required_attributes() != []:
        status = 'error'
      else:
        status = self.process_code(code)
      # find notebook on server side and execute
    reply_content = {
      'status': status,
      # The base class increments the execution count
      'execution_count': self.execution_count,
      'payload': [],
      'user_expressions': {}}

    return reply_content

if __name__ == '__main__':
  IPKernelApp.launch_instance(kernel_class=ERP5ClusterKernel)
