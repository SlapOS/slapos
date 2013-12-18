* This stack has for purpose to know if all promises, services, custom monitoring scripts went/are ok.

* If you want to use the monitoring stack:

1/ In the software.cfg of your Software Release, extends the stack
2/ In the template that will be copied for the buildout in the instance folder (instance.cfg ?), you have to add these parts:
  certificate-authority
  ca-nginx
  directory
  deploy-monitor-script
  deploy-rss-script
  cron
  cron-entry-monitor
  cron-entry-rss
  make-rss
  nginx-service
  slap-parameters

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