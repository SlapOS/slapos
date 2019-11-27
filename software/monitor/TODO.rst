edge
====

 * each slave checks one host passed by
 * each slave is:
   * url-checker storing info in the DB
   * promise checking status, which uses url-checker DB, preferrably via some
     url-checker provided tool
 * then promises are returned back to the monitor

Master parameters:

 * `certificate_expiration_days` default: 30
 * `http_code` default: 200
 * `dns` default: <empty>, list of DNS servers to use to resolve domains, region based

Slave parameters:

 * `url` default: NONE, required
 * `certificate_expiration_days` default: <MASTER>
 * `http_code` default: <MASTER>
