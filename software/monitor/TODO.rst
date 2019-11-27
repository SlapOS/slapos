edge
====

 * each slave checks one host passed by
 * default certificate expiration time and http code are configured on master
 * certificate expiration time and http code are configured on each slave
 * each slave is:
   * url-checker storing info in the DB
   * promise checking status, which uses url-checker DB, preferrably via some
     url-checker provided tool
 * then promises are returned back to the monitor
