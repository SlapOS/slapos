seleniumrunner
==============

Allows to run selenium tests through browser and xvfb. Posts the results on
Nexedi ERP5.

Parameters
==========

  * project : name of the project inside of ERP5 test result instance
  * user : username to use in ERP5 instance to test
  * password : password to use in ERP5 instance to test
  * suite_name : name of test suite to launch 
  * url : url to portal_test of ERP5 isntance to test
  * test_report_instance_url : url of test_result_module to put results

  * Example::
  
    <?xml version="1.0" encoding="utf-8"?>
    <instance>
    <parameter id="project">Vifib</parameter>
    <parameter id="user">myuser</parameter>
    <parameter id="password">mypassword</parameter>
    <parameter id="suite_name">my_zuite</parameter>
    <parameter id="url">https://myerp5totest/erp5/portal_tests</parameter>
    <parameter id="test_report_instance_url">https://user:passwordwww.myerp5withtestresults.com/test_result_module/</parameter>
    </instance>
