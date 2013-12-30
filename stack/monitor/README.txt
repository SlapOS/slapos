* This stack has for purpose to know if all promises, services, custom monitoring scripts went/are ok.
* The second purpose of this stack is to implement a zero-knowledge feature : it means you can use its control interface to provide the user with sensible data. It can also let the user change some parameters
* It also provides a web interface, to see which promises, services and custom scripts failed. It also provide a rss feed to easily know the actual state of your instance, and to know when it started to went bad.

Implementation :
----------------
1/ In the software.cfg of your Software Release, extends the stack
2/ In the template that will be copied for the buildout in the instance folder (instance.cfg ?), you have to add these parts:
###Parts to add for monitoring
  slap-parameters
  certificate-authority
  cron
  cron-entry-monitor
  cron-entry-rss
  deploy-monitor-cgi
  deploy-control-cgi
  deploy-monitor-script
  deploy-rss-script
  make-rss
  certificate-authority
  public
  zero-parameters
  cgi-httpd-wrapper
  publish-connection-informations

* If you want to add a custom monitoring script, you can write it (in whatever language you wish) and save it in YOUR_INSTANCE_FOLDER/etc/monitor.
The only thing to know, is that if your script successfully passed, do not return or print nothing. If there is a problem, you can print the explanation on stdout or stderr

* Here are 2 promises that you can add to your instance buildout, to see if it is working (one is ok, not the other) :
[google-promise]
recipe = slapos.cookbook:check_url_available
path = $${directory:promise}/google
url = http://www.google.com
dash_path = ${dash:location}/bin/dash
curl_path = ${curl:location}/bin/curl

[failing-promise]
recipe = slapos.cookbook:check_url_available
path = $${directory:promise}/fail
url = http://127.0.0.2
dash_path = ${dash:location}/bin/dash
curl_path = ${curl:location}/bin/curl


Notice :
--------
* /!\A default password is set up at the installation : "passwordtochange". It has to be rewritten in the control interface by the user itself
* /!\ If you use the recipe zeroknown, never name a parameter "recipe" or "password". 
* The control interface will let you change the values of the options declared in the [public] section of the config file (see zeroknown recipe). Other section's values will just be printed. These values won't be overwritten by buildout.
* If you want to allow a user to change, use the recipe zeroknown, with the buildout section name : "[public]"
* If you manually change a parameter, it could take some time for the modifications to be applied (at least 1 or 2 slapgrid-cp)
