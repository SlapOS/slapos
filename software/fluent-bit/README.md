# Fluent-bit

## When instantiating Fluent-bit you can use the following config:
```
release="https://lab.nexedi.com/nexedi/slapos/raw/master/software/fluent-bit/software.cfg"
supply(release, "COMP-****")
partition_parameter_kw = {
    "service": {
        "flush": 5,
        "daemon": "off",
        "log_level": "debug"
    },
    "input": {
        "name": "mqtt",
        "tag": "data",
        "listen": "0.0.0.0",
        "port": 1883
    },
    "output": {
        "name": "forward",
        "match": "*",
        "host": "127.0.0.1",
        "port": 24224
    }
}
filter_kw = {"computer_guid": "COMP-****"}
request(software_release = release, partition_reference='****', partition_parameter_kw=partition_parameter_kw, filter_kw = filter_kw)
```
