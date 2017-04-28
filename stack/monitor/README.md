Monitor stack
=============

* This stack has for purpose to know if all promises, services, custom monitoring scripts went/are ok.
* It also provides a web interface, to see which promises, instance and hosting subscription status. It also provide a rss feed to easily know the actual state of your instance, and to know when it started to went bad. You can also add your own monitoring scripts.


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
      ${monitor-template:rendered}
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
    username = ${monitor-htpasswd:username}
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
- password: monitor password, this should be the same in all sub-instances. Default is generated (${monitor-htpasswd:username}).
- instance-configuration: instance custom information or configuration to show in monitor web interface. There is many possibility:
  raw CONFIG_KEY VALUE => non editable configuration, ie: raw monitor-password resqdsdsd34
  file CONFIG_KEY PATH_TO_RESULT_FILE => editable configuration.
  httpdcors CONFIG_KEY PATH_TO_HTTP_CORS_CFG_FILE PATH_HTTPD_GRACEFUL_WRAPPER => show/edit cors domain in monitor
- configuration-file-path: path of knowledge0 cfg file where instance configuration will be written.
- interface-url: The URL of monitor web interface. This URL will be present in generated JSON files.

**Multiple Monitors**

If you have sub-instances, you should collect the base monitor url from all instances with monitor and send it to monitor-url-list or you can override "monitor-base-url-dict" section and add all the urls as key/value pairs in the root instance.

    [monitor-base-url-list]
    monitor1-url = https://[xxxx:xxx:xxxx:e:11::1fb1]:4200 
    monitor2-url = https://[xxxx:xxx:xxxx:e:22::2fb2]:4200 
    ..
    ..

Also, All monitors of the sub instances need to have same password as the password of the root instance monitor.

NB: You should use double $ (ex: $${monitor-template:rendered}) instead of one $ in your instance template file if it's not a jinja template. See:
- Jinja template file exemple, use one $: https://lab.nexedi.com/nexedi/slapos/blob/master/software/slaprunner/instance-resilient-test.cfg.jinja2
- Non Jinja template file, use $$: https://lab.nexedi.com/nexedi/slapos/blob/master/software/slaprunner/instance.cfg

Add a promise
-------------

Monitor stack will include slapos promise directory etc/promise to promise folder. All files in that directory will be considered as a promise.
This mean that all slapos promises will be checked frequently by monitor.


    [monitor-conf-parameters]
    ...
    promise-folder = ${directory:promises}
    ...


Monitor will run each promise every minutes and save the result in a json file. Here is an exemple of promise result:

    {"status": "ERROR", "change-time": 1466415901.53, "hosting_subscription": "XXXX", "title": "vnc_promise", "start-date": "2016-06-21 10:47:01", "instance": "XXXX-title", "_links": {"monitor": {"href": "MONITOR_PRIVATE_URL"}}, "message": "PROMISE_OUPT_MESSAGE", "type": "status"}

A promise will be ran during a short time and report the status: ERROR or OK, plus an ouput message which says what was good or bad.
The promise should not run for more that 20 seconds, else it will be interrupted because of time out. However this value can be modified from monitoring web interface, see parameter "promise-timeout" of your hosting subscription.
On slapos, the default timeout value is also 20 seconds, if the value is modified on monitor (ex: to 50 seconds), it will still fails when slapgrid will process instance if the promise execution exceed 20 seconds.

Promises result are published in web public folder, access URL is: MONITOR_BASE_URL/private/PROMISE_NAME.status.json
Everytime monitor will run a promise an history of result will be also updated. The promise history will be updated during one day, after that a new history will be created.
To access promise history file as JSON, use URL MONITOR_BASE_URL/private/PROMISE_NAME.history.json

Add a promise: monitor promise
------------------------------

Monitor promise is also a promise like normal promise script but it will be placed into the folder ${monitor-directory:promises}:

    [monitor-promise-xxxxx]
    recipe = slapos.recipe.template:jinja2
    rendered = ${monitor-directory:promises}/my-custom-monitor-promise

Theses promises will be executed only by monitor (not slapos) every minutes and will report same infor as default promises. This is another way to 
add more custom promises to check if server is overloaded, or if network start to be slow, etc...


Add custom scripts to monitor
-----------------------------

Custom script will be automatically run by the monitor and result will be reported in monitor private folder. To add your custom script in ${monitor-directory:reports} folder. Here is an example:

    [monitor-check-webrunner-internal-instance]
    recipe = slapos.recipe.template:jinja2
    template = ${monitor-check-webrunner-internal-instance:location}/${monitor-check-webrunner-internal-instance:filename}
    rendered = $${monitor-directory:reports}/$${:filename}
    filename = monitor-check-webrunner-internal-instance
    mode = 0744

The script will be executed every minutes by default. To change, put periodicity in script name:
  - monitor-check-webrunner-internal-instance_every_1_minute
  - monitor-check-webrunner-internal-instance_every_25_minute
  - monitor-check-webrunner-internal-instance_every_1_hour
  - monitor-check-webrunner-internal-instance_every_3_hour
  - ...

the script name should end with _every_XX_hour or _every_XX_minute. With this, we can set filename as:

    filename = monitor-check-webrunner-internal-instance_every_2_minute

You can get custom script results files at MONITOR_BASE_URL/private/FILE_NAME.


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

files in public directory are accessible at MONITOR_BASE_URL/public, and for private directory: MONITOR_BASE_URL/private.


Monitor RSS and OPML Feed
-------------------------

Monitor generate rss containing latest result for all promises, this feed will be upaded every minutes. The Rss fee URL is
MONITOR_BASE_URL/public/feed

OPML Feed is used to aggregate many feed URL, this is used on monitor to link many single monitor instances. For example, a resilient
webrunner has 5 instances at least, each instance has a monitor which leads to 5 monitor instances too. One main instance (usally the root instance)
will collect rss feeds of all others monitor's in a single OPML file. This file is published and used to configure a monitor backend to the web interface.
The URL of OPML feed is: MONITOR_BASE_URL/public/feeds


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
        |       |          |            |
      public  private  jio_public  jio_private
        X       Y          |            |
                    .jio_documents  .jio_documents
                           X            Y


MONITOR_BASE_URL/public or private is for normal HTTPS.
MONITOR_BASE_URL/share is the webdav URL. public/ and private/ are linked to public and private directories.
  webdav also has jio_public/.jio_documents and jio_private/.jio_documents which are linked to public and private directory and they works with jio webdav pluging.


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

Monitor has a paramters called "instance-configuration" from the section [monitor-instance-parameter]
that can be updated to specify which parameters will be deplayed on monitor web interface.

Parameters can be editable (except raw parameter) directly from  monitor interface. The change will be updated into the related file. Here are some examples:

    [monitor-instance-parameter]
    instance-configuration = 
      raw init-user ${publish-connection-information:init-user}
      htpasswd monitor-password ${monitor-htpassword-file:password-file} ${monitor-instance-parameter:username} ${httpd-monitor-htpasswd:htpasswd-path}
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
