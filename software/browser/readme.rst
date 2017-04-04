Browser as a service
####################

:author: Tomas Peterka

Accesses ``configuration.browser-url`` every ``configuration.browser-period``
hours by Firefox browser. Script ``browse-url.sh`` is managed by cron. It uses 
firefox to access given url. Browser has restricted time to run because script 
sends SIGKILL after ``configuration.browser-timeout`` seconds.
