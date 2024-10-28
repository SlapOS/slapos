Monitor stack
=============

* This stack has for purpose to know if all promises, services, custom monitoring scripts went/are ok.
* It also provides a web interface, to see promises, instances and hosting subscriptions status. It also provides a rss feed to easily know the actual state of your instance, and to know when it started to went bad. You can also add your own monitoring scripts.


Implementation :
----------------

1/ In your software.cfg, extends the stack:

    [buildout]
    extends =
      ...
      ../../stack/monitor/buildout.cfg

2/ In your instance.cfg file or instance template (instance-xxx.cfg.jinja2, ...),

Extend monitor template and a monitor-base to parts:

    [buildout]
    extends = 
      ${monitor-template:output}
    parts = 
      ...
      monitor-base

Override monitor configuration by adding monitor-instance-parameter section to define your custom parameters.

    [monitor-instance-parameter]
    monitor-title = ${slap-configuration:instance-title}
    monitor-httpd-ipv6 = ${slap-configuration:ipv6-random}
    monitor-httpd-port = ...
    monitor-base-url = ${monitor-frontend-promise:url}
    root-instance-title = ${slap-configuration:root-instance-title}
    monitor-url-list =
    cors-domains = monitor.app.officejs.com
    collector-db = ...
    password = ${monitor-htpasswd:passwd}
    username = admin
    instance-configuration = ...
    configuration-file-path = ...
    interface-url = ...

You don't need to define all parameters, you can only set what is required to be changed. ie:

    [monitor-instance-parameter]
    monitor-httpd-port = 8333


- monitor-title: is the title of the current software instance.
- root-instance-title: is the title of the hosting subscription.
- monitor-httpd-ipv6: is the ipv6 of the computer partition.
- monitor-httpd-port: the port to bind monitor httpd server on.
- monitor-base-url: this url will be used/showed in monitor interface. This url is present in some monitor generated output files. There can be two value, the default: ${monitor-frontend-promise:url} which access monitor httpd server through the frontend and ${monitor-httpd-conf-parameter:url} which is the url with ipv6 (https://[IPv6]:port/).
- monitor-url-list: set list of Monitor Base URL of monitor sub-instances, if this is the root instance with at least one child.
- cors-domains: the domain used by the monitor web interface. The default is: monitor.app.officejs.com.
- username: monitor username, this should be the same in all sub-instances. Default is: admin.
- password: monitor password, this should be the same in all sub-instances. Default is generated (${monitor-instance-parameter:username}).
- instance-configuration: instance custom information or configuration to show in monitor web interface. There is many possibility:
  raw CONFIG_KEY VALUE => non editable configuration, ie: raw monitor-password resqdsdsd34
  file CONFIG_KEY PATH_TO_RESULT_FILE => editable configuration.
  httpdcors CONFIG_KEY PATH_TO_HTTP_CORS_CFG_FILE PATH_HTTPD_GRACEFUL_WRAPPER => show/edit cors domain in monitor
- configuration-file-path: path of knowledge0 cfg file where instance configuration will be written.
- interface-url: The URL of monitor web interface. This URL will be present in generated JSON files.

**Multiple Monitors**

If you have sub-instances, you should collect the base monitor url from all instances with monitor and send it to monitor-url-list or you can override "monitor-base-url-dict" section and add all the urls as key/value pairs in the root instance.

    [monitor-base-url-dict]
    monitor1-url = https://[xxxx:xxx:xxxx:e:11::1fb1]:4200
    monitor2-url = https://[xxxx:xxx:xxxx:e:22::2fb2]:4200
    ..
    ..

Also, all monitors of the sub instances need to have same password as the password of the root instance monitor.

NB: You should use double $ (ex: $${monitor-template:output}) instead of one $ in your instance template file if it's not a jinja template. See:
- Jinja template file exemple, use one $: https://lab.nexedi.com/nexedi/slapos/blob/master/software/theia/instance-resilient.cfg.jinja
- Non Jinja template file, use $$: https://lab.nexedi.com/nexedi/slapos/blob/master/software/theia/instance.cfg.in

Add a promise
-------------

To learn how to write a promise in SlapOS, please read this document:

    https://www.erp5.com/slapos-TechnicalNote.General.SlapOS.Monitoring.Specifications

Writing a promise consists of defining a class called RunPromise which inherits from GenericPromise class and defining methods: anomaly(), sense() and test(). Python promises should be placed into the folder etc/plugin of the computer partition.
New promises should be placed into the folder etc/plugin, legacy promises are into the folder etc/promise. Legacy promises are bash or other executable promises script which does not use GenericPromise class.

You will use slapos.cookbook:promise.plugin to generate your promise script into `etc/plugin` directory. Adding a promise will look like this:

    [promise-check-site]
    <= monitor-promise-base
    module = check_socket_listening
    name = check_site.py
    config-host = ${publish:ipv6}
    config-port = 2020
    config-foo = bar

The section `monitor-promise-base` is defined in the monitor stack, `name` is the filename of the script that will be generated under `etc/plugin` directory, `module` is the name of your promise module (you can find a list of existing module in https://lab.nexedi.com/nexedi/slapos.toolbox/tree/master/slapos/promise/plugin).

Then you will have to add `promise-check-site` section to buildout parts, so it will be installed.

In your promise code, you will be able to call `self.getConfig('hostname')`, `self.getConfig('port')` and `self.getConfig('foo')`. The returned value is `None` if the config parameter is not set.

Slapgrid will run each promise every time a partition is processed (every minutes in theory), if the partition is up to date, slapgrid will only run promises anomaly check and save the result in a json file. Here is an exemple of promise result:

    {"result": {"date": "2018-03-22T15:35:07", "failed": false, "message": "buildout is OK", "type": "Test Result"}, "path": "PARTITION_DIRECTORY/etc/plugin/buildout-slappart0-status.py", "name": "buildout-slappart0-status.py", "execution-time": 0.1, "title": "buildout-slappart0-status"}

The promise execution time should be short, by default promise-timeout in slapgrid is to 20 seconds. If a promise runs in more than the defined promise-timeout, the process is killed and a "promise timed out" message is returned.
JSON in the folder `PARTITION_DIRECTORY/.slapgrid/promise/result`, and promise logs are in `PARTITION_DIRECTORY/.slapgrid/promise/log`.


Monitor will expose promise JSON result in web public folder, access URL is: `MONITOR_BASE_URL/public/promise/PROMISE_TITLE.status.json`. Log files are exposed in monitor private web folder,
access URL is: `MONITOR_BASE_URL/private/log/monitor/promise`

Add custom file or directory to monitor
---------------------------------------

Log or others files can be added in monitor public or private directory:

    [monitor-conf-parameters]
    public-path-list =
      /path/to/my/public/directory/
      ...
    private-path-list =
      ${directory:log}
      ...

files in public directory are accessible at `MONITOR_BASE_URL/public`, and for private directory: `MONITOR_BASE_URL/private`.


Monitor promise history, RSS and OPML Feed
------------------------------------------

Monitor read every minutes JSON promises result files to build Rss and full instance state. The Rss feed URL is
`MONITOR_BASE_URL/public/feed`

OPML Feed is used to aggregate many feed URL, this is used on monitor to link many single monitor instances. For example, a resilient
webrunner has 3 instances at least, each instance has a monitor which leads to 3 monitor instances too. One main instance (usally the root instance)
will collect rss feed of all others monitor's in a single OPML file. This file is published and used to configure a monitor backend to the web interface.
The URL of OPML feed is: `MONITOR_BASE_URL/public/feeds`

Everytime monitor will also produce history of for each promise in a single JSON file.
To access promise history file as JSON, use URL `MONITOR_BASE_URL/public/PROMISE_TITLE.history.json`

Monitor Base web directory tree
-------------------------------

                      MONITOR_BASE_URL
                            |
                --------------------------
                |           |             |
              share       public        private
            (webdav)        X             Y 
                |
        ---------------------------------
        |       |       
      public  private 
        X       Y     


MONITOR_BASE_URL/public or private is for normal HTTPS.
MONITOR_BASE_URL/share is the webdav URL. public/ and private/ are linked to public and private directories.


Access to Monitor
-----------------

In monitor instance.cfg file, the section [monitor-publish-parameters] contain information about monitor access.
Usefull information are monitor-base-url, monitor-url, monitor-user and monitor-password.

- ${monitor-publish-parameters:monitor-base-url} is the url of monitor httpd server.
- ${monitor-publish-parameters:monitor-base-url}/public/feed is the RSS url of this monitor instance.
- ${monitor-publish-parameters:monitor-base-url}/public/feeds is the OPML URL of this monitor instance. To setup monitor instance in your monitoring interface, use OPML URL of the root instance. It should contain URL to others monitor instances.
- ${monitor-publish-parameters:monitor-base-url}/private is the monitor private directory. Username and password are reqired to connect.

The section [monitor-publish] contain parameters to publish with your instance connection information. It will publish "monitor-base-url" and
"monitor-setup-url" which is used to configure your instance to monitor interface in one click.

To publish configuration URL in your instance.cfg, you can do like this:

    [publish-connection-information]
    <= monitor-publish
    ...
    custom-parameter-one = xxxxx
    custom-parameter-two = yyyyy


Send parameters to monitor interface
------------------------------------

Monitor has a paramters called "instance-configuration" from the section [monitor-instance-parameter] that can be updated to specify which parameters will be deployed on monitor web interface.

Parameters can be editable (except raw parameter) directly from  monitor interface. The change will be updated into the related file. Here are some examples:

    [monitor-instance-parameter]
    instance-configuration = 
      raw init-user ${publish-connection-information:init-user}
      htpasswd monitor-password ${httpd-monitor-htpasswd:password-file} ${monitor-instance-parameter:username} ${httpd-monitor-htpasswd:htpasswd-path}
      file promise-timeout ${monitor-promise-timeout-file:file}

The user will see parameters:
- init-user (non editable)
- monitor-password (editable)
- promise-timeout (editable)

htpasswd: is used to change apache htpasswd directly from monitor interface. The syntax is like:

    htpasswd PARAMETER_ID PASSWORD_TEXT_FILE HTPASSWD_USER_NAME HTPASSWD_FILE

PASSWORD_TEXT_FILE contain the password which is showed to the user.

file: is used to edit a parameter directly into file. Parameter is read and write into the provided file

    file PARAMETER_ID PATH_TO_THE_FILE

raw: is a non editable paramter.

    raw PARAMETER_ID TEXT_VALUE

httpdcors: used to edit an apache http_cors.conf file, this file should be include in the main apache configuration file

    httpdcors PARAMETER_ID PATH_TO_HTTP_CORS_CFG_FILE PATH_HTTPD_GRACEFUL_WRAPPER

PATH_HTTPD_GRACEFUL_WRAPPER will be executed to reload apache configuration after modification is done.
