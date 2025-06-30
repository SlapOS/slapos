# grafana / fluent-bit + loki / telegraf + influxdb

This is an experimental integration, mainly to evaluate these solutions.

## SlapOS / ERP5 integration

By using `applications` instance parameter, the instanciated agent will ingest log
files in loki and some metrics in influxdb.

This current experimental can ingest logs and metrics from slapos partitions, as long
as the slapos user running the agent can have access to the files. This part is the
problematic part and the reason why the plan is to integrate the agent from in the
monitoring stack running in each partition. For now, the agent instance creates a
`parts/facl-script` script that can be executed to use `setfacl` command to give access
to the user.

The next steps of the plans are to move the agent parts directly in ERP5 software
release.

## Grafana

A default user is created, username and password are published as connection
parameters. You can add more users in grafana interface.

Datasources should be automatically added.


## Custom telegraf plugins

telegraf is a software used to collect some metrics. It should be possible to replace
it by fluent-bit.

See https://github.com/influxdata/telegraf to learn about plugins.

Useful plugins in this context are probably
[exec](https://github.com/influxdata/telegraf/tree/v1.17.3/plugins/inputs/exec),
[logparser](https://github.com/influxdata/telegraf/tree/v1.17.3/plugins/inputs/logparser)
or
[http](https://github.com/influxdata/telegraf/tree/v1.17.3/plugins/inputs/http).

Telegraf will save in the `telegraf` database from the embedded influxdb server.


## Influxdb

Influxdb backups are not done automatically by this software release.

One important thing to notice is that the backup protocol is enabled on ipv4
provided by slapos, so make sure this ip is not reachable from untrusted
sources.

## Loki

Loki is the database for logs, see `TestLoki` in test for an example, or the
ERP5 integration.
