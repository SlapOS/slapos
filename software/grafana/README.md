# grafana / telegraf / influxdb

This is an experimental integration, mainly to evaluate these solutions.

## Custom telegraf plugins


See https://github.com/influxdata/telegraf to learn about plugins.

Useful plugins in this context are probably
[exec](https://github.com/influxdata/telegraf/tree/v1.17.3/plugins/inputs/exec),
[logparser](https://github.com/influxdata/telegraf/tree/v1.17.3/plugins/inputs/logparser)
or
[http](https://github.com/influxdata/telegraf/tree/v1.17.3/plugins/inputs/http).

Telegraf will save in the `telegraf` database from the embedded influxdb server.


## Grafana

A default user is created, username and password are published as connection
parameters. You can add more users in grafana interface.

Datasources should be automatically added.

## Influxdb

Influxdb backups are not done automatically by this software release.

One important thing to notice is that the backup protocol is enabled on ipv4
provided by slapos, so make sure this ip is not reachable from untrusted
sources.

# Ingesting/Visualizing logs

Eventhough main feature is visualizing metrics, Grafana has a feature called "Explore" to view logs for a time frame.
The following backend can be used:

## Loki

See `TestLoki` in test for an example.

## Influxdb

Influxdb logs only have tags and there does not seem to be a way to search (except than tag and time frame).

To inject log files containing:
```
INFO the message
WARN another message
```

use config like:

```
[[inputs.logparser]]
  files = ["/tmp/x*.log", "/tmp/aaa.log"]

  [inputs.logparser.grok]
  measurement = "logs"
  patterns = ['^%{WORD:level:tag} %{GREEDYDATA:message:string}']
```
