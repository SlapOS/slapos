BOINC Server
============

Introduction
------------

The Berkeley Open Infrastructure for Network Computing (BOINC) is an open 
source middleware system for volunteer and grid computing.
http://boinc.berkeley.edu/trac/wiki/ProjectMain

This Software Release is used to deploy an instance of BOINC server on SlapOS

How it work?
------------

The following example show how to request an instance of BOINC server.

BOINC Server Parameters :

- project: The name of your project. Default is project=boinc_test
- full-name: Full name of your project. Default is full-name=Boinc Project SAMPLE
- domain: Use this parameter if you want to define by hand the url of your project.
Ex: domain = http://myboinc.host-dommain.com
- copyright-holder: The name of your compagny. It will be displayed at the footer of
your BOINC project website.

Job Submission Parameters:

- default-template-result (Default is ${boinc-default:template-result}): Set the
default Output Template to use when creating a BOINC work unit.
- default-template-wu (Default is ${boinc-default:template-wu}): Set the
default Input Template to use when creating a BOINC work unit.
- default-extension (Default is ${boinc-default:extension}): For example in windows if 
job executable is an .exe, set default-extension=exe
- default-platform (Default is ${boinc-default:platform}): Set the default platform
for job submission. http://boinc.berkeley.edu/trac/wiki/BoincPlatforms
- boinc-app-list: Use this json parameter to submit your job list to BOINC Server.
For exemple: 

boinc-app-list = {"APP_NAME":
                        {"APP_VERSION":
                            {"use_default":true, "binary":"PATH/URL_OF_BINARY",
                            "wu-number":NUM, "input-file":"PATH/URL_OF_INPUT_FILE"},
                        "APP_VERSION2":
                            {"use_default":false, "binary":"PATH/URL_OF_BINARY",
                            "wu-number":NUM, "input-file":"PATH/URL_OF_INPUT_FILE",
                            "extension":"", "platform":"x86_64-pc-linux-gnu",
                            "template-result":"PATH/URL_OF_OUTPUT_TEMPLATE",
                            "template-wu":"PATH/URL_OF_INPUT_TEMPLATE"}
                  }, ...}

APP_NAME example: upper_case (without space)
APP_VERSION examples: 1.00, 2.10, 1.10

Request your instance:

This is a minimal parameter to use:
<?xml version="1.0" encoding="utf-8"?>
<instance>
  <parameter id="project">Sample</parameter>
  <parameter id="full-name">My BOINC project Sample</parameter>
  <parameter id="copyright-holder">my.compagny.com</parameter>
  <parameter id="boinc-app-list">JSON-JOB-LIST</parameter>
</instance>

Note: - You can update boinc-app-list anytime, this would allow you to update the 
nomber of work unit, or to modify files. For any job modification, APP_NAME and 
APP_VERSION is required.
- To create another BOINC project, please request another instance on SlapOS.

Warning: Once your project has been started (and BOINC client is connected on current
server), don't change the project name, otherwise this would cause the lost of current project.



Connect to your instance
------------------------

When your instance is ready, SlapOS must provide 3 URL:
boinc_home_page  URL_BASE/PROJECT/  (public web page, BOINC Client will use this URL 
to connect to your server)
boinc_admin_page	URL_BASE/PROJECT_ops/ (administrative web page)
boinc_result_url URL_BASE/PROJECT_result/ (result web page, this page will allow
you to show job result)

