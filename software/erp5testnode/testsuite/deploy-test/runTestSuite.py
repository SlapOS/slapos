from __future__ import print_function
import argparse
import os
import glob
from time import gmtime, strftime, time, sleep
from erp5.util import taskdistribution, testsuite
import logging
import sys
import tempfile
import json


SLEEP_TIME = 10
TRY_AMOUNT = 3600


def waitForSite(partition_path):
  status_dict = {'command': 'file not found'}

  # find test result, wait 10h
  try_num = 1
  start = time()
  result_found = False
  while 1:
    finished = False
    try_info = 'Try %s/%s: ' % (try_num, TRY_AMOUNT)
    test_result_glob = os.path.join(
        partition_path,
        '..',
        '*',
        'srv',
        'public',
        'test-script-result',
    )
    print(try_info + 'Waiting for data in %r.' % (test_result_glob,))
    result_list = glob.glob(test_result_glob)
    if len(result_list) > 0:
      result_path = result_list[0]
      print(try_info + 'Data directory %r found, looking for results.' % (
            result_path,))
      result_file_list = list((
          os.path.join(dirname, filename)
          for dirname, dirnames, filenames in os.walk(result_path)
          for filename in filenames
      ))
      if len(result_file_list):
        print(try_info + 'No result posted, will check next try.')
      for result_file in result_file_list:
        print(try_info + 'Data found.')
        result_found = True
        result_file = os.path.abspath(result_file)
        status_dict['command'] = result_file
        result = open(result_file).read()
        # remove result, as it is not required anymore
        os.unlink(result_file)
        print(try_info + 'Analysis of result %r:' % (result_file,))
        print(try_info + result)
        status_dict['stderr'] = 'Last result:\n%s' % (result,)
        if 'FATAL: all hosts have already failed -- aborting' in result:
          # failed
          status_dict.update(
              success=False
          )
          finished = False
          status_dict['stdout'] = try_info + 'Build not yet successful.'
          print(try_info + '%r: Found not yet finished run.' % (result_file,))
        elif "\"msg\": \"[u'Build successful, connect to:', u'" in result:
          # success
          status_dict.update(
              success=True
          )
          finished = True
          print(try_info + '%r: Found finished successful run.' % (
              result_file,))
          status_dict['stdout'] = try_info + 'Build successful.'
          break
        else:
          # unknown
          status_dict.update(
              success=False

          )
          status_dict['stdout'] = \
              try_info + 'Cannot find success nor failure result in the output'
          print(try_info + '%r: Found unknown run.' % (result_file,))
          finished = False
    if finished:
      break
    if try_num >= TRY_AMOUNT:
      msg = try_info + 'Time exceeded, success not found.'
      print(msg)
      status_dict.setdefault('stdout', '')
      status_dict['stdout'] = '\n'.join([status_dict['stdout'], msg])
      break
    try_num += 1
    print(try_info + 'Sleeping for %ss.' % (SLEEP_TIME,))
    sleep(SLEEP_TIME)
  if not result_found:
    status_dict['stdout'] = try_info + 'Test timed out and no result found.'
    status_dict.update(
        success=False

    )
  end = time()
  status_dict.update(
      date=strftime("%Y/%m/%d %H:%M:%S", gmtime(end)),
      duration=end - start,
  )
  return status_dict


def main():
  logger = logging.getLogger()
  logger.addHandler(logging.StreamHandler(sys.stdout))
  logger.setLevel(logging.DEBUG)
  parser = argparse.ArgumentParser(description='Run a test suite.')
  parser.add_argument('--test_suite', help='The test suite name')
  parser.add_argument('--test_suite_title', help='The test suite title')
  parser.add_argument('--test_node_title', help='The test node title')
  parser.add_argument('--project_title', help='The project title')
  parser.add_argument('--revision', help='The revision to test',
                      default='dummy_revision')
  parser.add_argument('--node_quantity', type=int,
                      help='Number of CPUs to use for the VM')
  parser.add_argument('--master_url',
                      help='The Url of Master controlling test suites')
  # SlapOS and deploy test specific
  parser.add_argument(
      '--partition_path',
      help="Path of a partition",
      default=os.path.abspath(os.getcwd()))
  parser.add_argument(
      '--test_reference',
      help="Reference of the test",
      default="missing"
  )
  parser.add_argument(
      '--partition_ipv4',
      help="IPv4 of a partition"
  )
  parser.add_argument(
      '--test_location',
      help="Location of the tests"
  )

  args = parser.parse_args()

  revision = args.revision
  test_suite_title = args.test_suite_title or args.test_suite
  os.environ['SOURCE_CODE_TO_TEST'] = args.test_location
  suite = testsuite.EggTestSuite(
      1, test_suite=args.test_suite, node_quantity=args.node_quantity,
      revision=revision)
  access_url_http = None
  access_url_https = None
  if args.partition_ipv4:
    access_url_http = 'http://%s:10080' % (args.partition_ipv4,)
    access_url_https = 'https://%s:10443' % (args.partition_ipv4,)
    os.environ['TEST_ACCESS_URL_HTTP'] = access_url_http
    os.environ['TEST_ACCESS_URL_HTTPS'] = access_url_https
  tool = taskdistribution.TaskDistributionTool(
      args.master_url,
      logger=logger)
  test_result = tool.createTestResult(
      revision, suite.getTestList(), args.test_node_title,
      suite.allow_restart, test_suite_title, args.project_title)
  if test_result is None:
    return

  # Create the site
  status_dict = waitForSite(args.partition_path)

  status_file = tempfile.NamedTemporaryFile()
  status_file.write(json.dumps(status_dict))
  status_file.flush()
  os.fsync(status_file.fileno())
  os.environ['TEST_SITE_STATUS_JSON'] = status_file.name

  assert revision == test_result.revision, (revision, test_result.revision)
  while suite.acquire():
    test = test_result.start(suite.running.keys())
    if test is not None:
      suite.start(test.name, lambda status_dict,
                  __test=test: __test.stop(**status_dict))
    elif not suite.running:
      break
  return

if __name__ == "__main__":
    main()
