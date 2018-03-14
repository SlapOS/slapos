# grafana / telegraf / influxdb

 
## Custom telegraf plugins


See https://github.com/influxdata/telegraf to learn about plugins.

Useful plugins in this context are probably
[exec](https://github.com/influxdata/telegraf/tree/1.5.1/plugins/inputs/exec)
or
[httpjson](https://github.com/influxdata/telegraf/tree/1.5.1/plugins/inputs/httpjson).

Telegraf will save in the `telegraf` database from the embedded influxdb server.


## Grafana

You'll have to add yourself the influxdb data source in grafana, using the
parameters published by the slapos instance.

http://docs.grafana.org/features/datasources/influxdb/

When adding datasource, use *proxy* option, otherwise Grafana makes your
browser query influxdb directly, which also uses a self signed certificate.
One workaround is to configure your browser to also accept influxdb certificate
before using grafana, but using proxy seems easier.

## Influxdb

Influxdb backups are not done automatically by this software release.

One important thing to notice is that the backup protocol is enabled on ipv4
provided by slapos, so make sure this ip is not reachable from untrusted
sources.

## TODO

* influxdb and telegraf runs with very low priority, this could become an option
* make one partition for each service and use switch software type
* make it easier to add custom configuration (how ?)
