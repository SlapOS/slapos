Software types
==============
Which software type is an entry point and can be used for root software
instance.

Parameters are expected to be passed as of *.serialised recipes expect them.
Minimal parameters::

```
<?xml version='1.0' encoding='utf-8'?>
<instance>
  <parameter id="_">{
    "cluster": "dummy",
  }</parameter>
</instance>
```

For each available key in the outmost dict are described below.

default (default)
-----------------
Deploy a NEO cluster.

'cluster' (str, mandatory)
~~~~~~~~~~~~~~~~~~~~~~~~~~
Cluster unique identifier. Your last line of defense against mixing up neo
clusters and corrupting your data. Choose a unique value for each of your
cluster.

'partitions' (int, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Number of partitions. You cannot change this value once you created a cluster.
Defaults to 12.

'replicas' (int, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~
Number of replicates.
Defaults to 0 (no resilience).

'node-list' (list, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
List of dictionaries. Defaults to list containing one empty dictionary.
One can specify following parameters in each of the dictionary.

* 'storage-count': Number of storage nodes to deploy. Defaults to 1.
  One master and one admin node is deployed with each storage.

* 'mysql': Dictionary containing configuration options for MySQL.

