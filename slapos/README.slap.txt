slap
====

Simple Language for Accounting and Provisioning python library.

Developer note - python version
-------------------------------

This library is used on client (slapgrid) and server side.
Server is using python2.4 and client is using python2.6
Having this in mind, code of this library *have* to work
on python2.4

How it works
------------

The SLAP main server which is in charge of service coordination receives from participating servers the number of computer paritions which are available, the type of resource which a party is ready provide, and request from parties for resources which are needed.

Each participating server is identified by a unique ID and runs a slap-server daemon. This dameon collects from the main server the installation tasks and does the installation of resources, then notifies the main server of completion whenever a resource is configured, installed and available.

The data structure on the main server is the following:

A - Action: an action which can happen to provide a resource or account its usage
CP - Computer Partition: provides a URL to Access a Cloud Resource
RI - Resource Item: describes a resource
CI - Contract Item: describes the contract to attach the DL to (This is unclear still)
R - Resource: describes a type of cloud resource (ex. MySQL Table) is published on slapgrid.org
DL - Delivery Line: Describes an action happening on a resource item on a computer partition
D - Delivery: groups multiple Delivery Lines

