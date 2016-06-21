Monitor stack
=============

* This stack has for purpose to know if all promises, services, custom monitoring scripts went/are ok.
* It also provides a web interface, to see which promises, instance and hosting subscription status. It also provide a rss feed to easily know the actual state of your instance, and to know when it started to went bad. You can also add your own monitoring scripts.


Implementation :
----------------

1/ In your software.cfg, extends the stack:

    [buildout]
    extends =
      ../../stack/monitor/buildout.cfg
      ...

2/ In your instance.cfg file or instance template, override monitor configuration section to define your custom parameters.

    [monitor-instance-parameter]
    monitor-title = ${slap-configuration:instance-title}
    monitor-httpd-ipv6 = ${slap-configuration:ipv6-random}
    monitor-httpd-port = ...
    monitor-base-url = ${monitor-frontend-promise:url}
    root-instance-title = ${slap-configuration:root-instance-title}
    opml-url-list =
    cors-domains = monitor.app.officejs.com
    collector-db = ...
    password = ${monitor-htpasswd:passwd}
    username = ${monitor-htpasswd:username}
    instance-configuration = ...
    configuration-file-path = ...

You don't need to define all parameters, you can only set what is required to be changed. ie:

    [monitor-instance-parameter]
    monitor-httpd-port = 8333


- monitor-title: is the title of the current software instance.
- root-instance-title: it the title of the hosting subscription.
- monitor-httpd-ipv6: is the ipv6 of the computer partition.
- monitor-httpd-port: the port to bind monitor httpd server on.
- monitor-base-url: this url that will be used/showed in monitor interface. This url is present in some monitor generated output files. There can be two value, the default: ${monitor-frontend-promise:url} which access monitor httpd server through the frontend and ${monitor-httpd-conf-parameter:url} which is the url with ipv6 (https://[IPv6]:port/).
- opml-url-list: list of OPML URL of monitor sub-instances, if this is the root instance with at least one child.
- cors-domains: the domain used by the monitor web interface. The default is: monitor.app.officejs.com.
- username: monitor username, this should be the same in all sub-instances. Default is: admin.
- password: monitor password, this should be the same in all sub-instances. Default is generated (${monitor-htpasswd:username}).
- instance-configuration: instance custom information or configuration to show in monitor web interface. There is many possibility:
  raw CONFIG_KEY VALUE => non editable configuration, ie: raw monitor-password resqdsdsd34
  file CONFIG_KEY PATH_TO_RESULT_FILE => editable configuration.
  httpdcors CONFIG_KEY PATH_TO_HTTP_CORS_CFG_FILE PATH_HTTPD_GRACEFUL_WRAPPER => show/edit cors domain in monitor
- configuration-file-path: path of knowledge0 cfg file where instance configuration will be written.

Example of custom monitor-instance-parameter: https://lab.nexedi.com/nexedi/slapos/blob/master/software/slaprunner/instance-runner.cfg#L726


Add a monitor promise
---------------------

By default, monitor stack will include slapos promise directory etc/promise to promise folder. All files in that directory will be considered as a promise.

    [monitor-conf-parameters]
    promise-folder-list =
      ${directory:promises}
      ${directory:monitor-promise}
    
Monitor will run each promise every minutes and save the result in a json file. Here is an exemple of promise result:

    {"status": "ERROR", "change-time": 1466415901.53, "hosting_subscription": "XXXX", "title": "vnc_promise", "start-date": "2016-06-21 10:47:01", "instance": "XXXX-title", "_links": {"monitor": {"href": "MONITOR_PRIVATE_URL"}}, "message": "PROMISE_OUPT_MESSAGE", "type": "status"}


Add log directory to monitor
----------------------------

Log or others files can be added in monitor public or private directory:

    [monitor-conf-parameters]
    public-path-list =
      ...
    private-path-list =
      ${directory:log}

files in public directory are accessible at MONITOR_BASE_URL/public, and for private directory: MONITOR_BASE_URL/private.


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
  - monitor-check-webrunner-internal-instance_every_5_minute
  - monitor-check-webrunner-internal-instance_every_1_hour
  - monitor-check-webrunner-internal-instance_every_3_hour
  - ...

the script name should end with _every_XX_hour or _every_XX_minute. With this, we can set filename as:

    filename = monitor-check-webrunner-internal-instance_every_2_minute

You can get custom script results files at MONITOR_BASE_URL/private/FILE_NAME.

Access to Monitor
-----------------

In monitor instance.cfg file, the section [publish] contain information about monitor access.
Usefull information are monitor-base-url, monitor-url, monitor-user and monitor-password.

- ${publish:monitor-base-url} is the url of monitor httpd server.
- ${publish:monitor-base-url}/public/feed is the RSS url of this monitor instance.
- ${publish:monitor-base-url}/public/feeds is the OPML URL of this monitor instance. To setup monitor instance in your monitoring interface, use OPML URL of the root instance. It should contain URL to others monitor instances.
- ${publish:monitor-base-url}/private is the monitor private directory. Username and password are reqired to connect.

To publish configuration URL in your instance.cfg, you can do like this:

    [publish-connection-information]
    ...
    monitor-setup-url = https://monitor.app.officejs.com/#page=settings_configurator&url=${publish:monitor-url}&username=${publish:monitor-user}&password=${publish:monitor-password}

