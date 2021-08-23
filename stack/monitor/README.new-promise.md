How to use the new promises
=============

Main changes: 

* There are new librairies in the monitor stack such as pandas, scipy and statsmodels.
* In slapos.toolbox, there are two new promises that can be used in the monitor stack.

Description of the new promises
-------------------------------

* `check_free_disk_space`: by default, has the same behavior as the current promise i.e. checks that there is at least 5% storage space left on the disk. There are now two options: 
  - `display_prediction`: thanks to ARIMA, the promise predicts the storage disk space in 10 days by default. If the remaining space is smaller than the threshold (same threshold as before i.e. 5%), then the promise returns a warning. This option uses the disk table from the database. It uses statsmodels, pandas and numpy.
  - `display_partition`: if the current disk size is smaller than the threshold, then the promise returns an error and the 3 biggest partitions of the computer. This option uses the folder table from the database. It doesn't use any new librairies.
* `monitor_partition_space`: detects bugs/anomalies by observing the behavior of partitions. For example, if a user suddenly uses a lot of disk space (related to a bug), then the promise returns an error. The promise uses the folder table from the database because it is intended to be used only on erp5 instance. It uses pandas and numpy.

Add librairies on monitor stack
-------------------------------

The goal is to be able to use the pandas libraries in the `monitor_partition_space` promise and pandas/scipy/statsmodels in the `check_free_disk_space` promise. For that, we have to add to the monitor stack:

1/ In buildout.cfg, extend the components and specify the versions:

    [buildout]
    extends =
      ...
      ../../component/pandas/buildout.cfg
      ../../component/statsmodels/buildout.cfg
      ../../component/scipy/buildout.cfg

    parts =
      ...
      slapos-toolbox

    [slapos.toolbox-dev]
    recipe = zc.recipe.egg:develop
    egg = slapos.toolbox
    setup = ${slapos.toolbox-repository:location}
    depends = ${slapos-toolbox-dependencies:eggs}

    [slapos-toolbox]
    eggs = ${slapos.toolbox-dev:egg}

    [slapos-toolbox-dependencies]
    eggs =
      ${lxml-python:egg}
      ${pycurl:egg}
      ${python-cryptography:egg}
      ${backports.lzma:egg}
      ${pandas:egg}
      ${statsmodels:egg}
      ${scipy:egg}

    [versions]
    ...
    scipy = 1.0.1
    statsmodels = 0.8.0
    patsy = 0.4.1
    pandas = 0.19.2

2/ In buildout.cfg, add a gcc section:

    [gcc]
    max_version = 0

Now, the new libraries will compile by default and we can use the new promises.

Use new promises in a software release
--------------------------------------

1/ In instance-monitor.cfg.jinja2, add:

    [monitor-instance-parameter]
    ...
    threshold-check-free-disk-space =
    days-check-free-disk-space =
    display-partition-check-free-disk-space = 1
    display-prediction-check-free-disk-space = 0

    [promise-check-free-disk-space]
    <= monitor-promise-base
    eggs = slapos.toolbox[prediction]
    ...
    config-threshold = ${monitor-instance-parameter:threshold-check-free-disk-space}
    config-nb-days-predicted = ${monitor-instance-parameter:days-check-free-disk-space}
    config-display-partition = ${monitor-instance-parameter:display-partition-check-free-disk-space}
    config-display-prediction = ${monitor-instance-parameter:display-prediction-check-free-disk-space}

    [promise-monitor-partition-space]
    <= monitor-promise-base
    eggs = slapos.toolbox[pandas]
    module = monitor_partition_space
    name = monitor-partition-space.py
    config-collectordb = ${monitor-instance-parameter:collector-db}
    config-threshold-ratio =

The `display-partition-check-free-disk-space` parameter is, by default, set to True. Don't forget to update the md5sum in buildout.hash.cfg.

2/ In any software release that extends the monitor stack, add this in instance-xxxx.cfg.jinja if you want to potentially use ARIMA option:

    [monitor-instance-parameter]
    # change the value of "display-prediction" to 1 to use ARIMA in the check_free_disk_space promise
    display-prediction-check-free-disk-space = {{ parameter_dict.get('display-prediction', 0) }}
    # by default the prediction will be for the next 10 days, this parameter can be changed below
    days-check-free-disk-space =

And/or you can add this to potentially use the new `monitor_partition_space` promise:

    {%- if parameter_dict.get('display-anomaly') in ('True', 'on', '1') %}
    [monitor-base]
    extra-depends = $${promise-monitor-partition-space:name}
    {%- endif %}

Don't forget to update the md5sum in buildout.hash.cfg.

3/ Request an instance:

> slapos request $INSTANCE_NAME $SR

The promise of the instance will act as before, but the promise `check_free_disk_space` will display the three biggest partitions on the machine if the remaining storage space is smaller than the threshold.

> slapos request $INSTANCE_NAME $SR --parameters display-prediction=1

If the remaining storage space is larger than the threshold, then the promise `check_free_disk_space` will make a prediction of the remaining storage space in 10 days.

> slapos request $INSTANCE_NAME $SR --parameters display-anomaly=1

The promise `check_free_disk_space` will only display the three biggest partitions on the machine if the remaining storage space is smaller than the threshold. The promise `monitor_partition_space` is activated.

> slapos request $INSTANCE_NAME $SR --parameters display-anomaly=1 display-prediction=1

Both promises are fully activated.
