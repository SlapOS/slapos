# End To End Testing

This software release is used to run end-to-end test of SlapOS softwares on an actual SlapOS cloud such as Rapid.Space. Since it can supply softwares and request instances on an actual cloud, it needs a SlaPOS client certificate.

Input parameters:

```
{
  "client.crt": <content of client.crt>
  "client.key": <content of client.key>
  "master-url": <url of SlapOS master>
}
```

A convenience script `generate_parameters.py` is provided to compute these parameters in JSON format from an existing SlapOS client configuration:

```
python3 generate_parameters.py --cfg <path to slapos-client.cfg> -o <output path>
```
