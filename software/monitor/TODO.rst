edge
====

 * monitor url-checker itself -- check that it run in last 30 minutes
 * each slave checks one host passed by
 * each slave is:
   * url-checker storing info in the DB
   * promise checking status, which uses url-checker DB, preferrably via some
     url-checker provided tool
 * then promises are returned back to the monitor
