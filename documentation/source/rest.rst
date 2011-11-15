SlapOS Master REST API (v1)
***************************

Find your SSL keys
------------------

You can find  X509 key/certificate to authentificate on the SlapOS Master.
Visit https://www.vifib.net/.

Exchange format
---------------

SlapOS master will support both XML and JSON formats for input and output.
When you make an API request, you will have to specify which format you want to
manage by setting it at the end of the route (.json or .xml)::

  POST http://example.com/api/v1/request.json
  POST http://example.com/api/v1/request.xml

Response status code
--------------------

Success
+++++++

``GET`` requests will return a ``"200 OK"`` response if the resource is successfully retrieved.

``POST`` requests which create a resource we will return a ``"201 Created"`` response if successful.

``POST`` requests which perform some other action such as sending a campaign
will return a ``"200 OK"`` response if successful.

``PUT`` requests will return a ``"200 OK"`` response if the resource is successfully updated.

``DELETE`` requests will return a ``"200 OK"`` response if the resource is successfully deleted.

Error
+++++

If you attempt to authenticate with an ``invalid SSL key`` or you attempt to use an
invalid ID for a resource, you'll received a ``"403 Forbidden"`` response.

If there is an ``error in your input``, you'll receive a ``"400 Bad Request"`` response, with details of the error.

If you attempt to request a ``resource which doesn't exist``, you'll receive a
``"404 Not Found"`` response.

If an ``unhandled error occurs`` on the API server for some reason, you'll
receive a ``"500 Internal Server Error"`` response.

Instance Methods
****************

Requesting a new instance
-------------------------

Request a new instanciation of a software.

`Request`::

  `POST` http://example.com/api/v1/request.{xml|json}

`Expected Request Body`::

  {
    "title": "My unique instance",
    "software_release": "http://example.com/example.cfg",
    "software_type": "type_provided_by_the_software",
    "slave": False,
    "status": "started",
    "parameter": {
      "Custom1": "one string",
      "Custom2": "one float",
      "Custom3": ["abc", "def"],
      },
    "sla": {
      "computer_id": "COMP-0",
      }
  }

`Expected Response`::

  HTTP/1.1 201 Created
  Content-Type: application/json; charset=utf-8

  {
    "instance_id": "azevrvtrbt",
    "status": "started",
    "connection": {
      "custom_connection_parameter_1": "foo",
      "custom_connection_parameter_2": "bar"
    }
  }

`Error Responses`:

* ``400 Bad Request`` The request body does not follow the API (one argument is missing or malformed).

* ``402 Payment Required`` The request can not be fullfilled because account is locked.

* ``409 Conflict`` The request can not be process because of the current status of the instance (sla changed, instance is under deletion, software release can not be changed, ...).

* ``202 Accepted`` The request has been accepted for processing::

    {
      "instance_id": "azevrvtrbt",
      "status": "starting"
    }

Deleting an instance
--------------------

Request the deletion of an instance.

`Request`::

   `DELETE` http://example.com/api/v1/instance/{instance_id}.{xml|json}

`Route values`:

* ``instance_id``: the ID of the instance

`No Expected Request Body`

`Expected Response`::

  HTTP/1.1 202 Accepted
  Content-Type: application/json; charset=utf-8
  {
    "status": "under deletion",
  }

`Error Responses`:

* ``400 Bad Request`` The request body does not follow the API (one argument is missing or malformed).

* ``402 Payment Required`` The request can not be fullfilled because account is locked.

* ``404 Not Found`` The instance can not be found.

* ``409 Conflict`` The request can not be process because of the current status of the instance.

Get instance information
------------------------

Request all instance informations.

`Request`::

   `GET` http://example.com/api/v1/instance/{instance_id}.{xml|json}

`Route values`:

* ``instance_id``: the ID of the instance

`No Expected Request Body`

`Expected Response`::

  HTTP/1.1 200 OK
  Content-Type: application/json; charset=utf-8
  {
    "instance_id": "azevrvtrbt",
    "status": "started",
    "software_release": "http://example.com/example.cfg",
    "software_type": "type_provided_by_the_software",
    "slave": False,
    "connection": {
      "custom_connection_parameter_1": "foo",
      "custom_connection_parameter_2": "bar"
    },
    "parameter": {
      "Custom1": "one string",
      "Custom2": "one float",
      "Custom3": ["abc", "def"],
      },
    "sla": {
      "computer_id": "COMP-0",
      }
    "children_id_list": ["subinstance1", "subinstance2"],
    "partition": {
      "public_ip": "::1",
      "private_ip": "127.0.0.1",
      "tap_interface": "tap2",
    },
  }

`Error Responses`:

* ``400 Bad Request`` The request body does not follow the API (one argument is missing or malformed).

* ``402 Payment Required`` The request can not be fullfilled because account is locked.

* ``404 Not Found`` The instance can not be found.

* ``409 Conflict`` The request can not be process because of the current status of the instance

Get instance authentification certificates
------------------------------------------

Request the instance certificates.

`Request`::

   `GET` http://example.com/api/v1/instance/{instance_id}/getcertificate.{xml|json}

`Route values`:

* ``instance_id``: the ID of the instance

`No Expected Request Body`

`Expected Response`::

  HTTP/1.1 200 OK
  Content-Type: application/json; charset=utf-8
  {
    "ssl_key": "...",
    "ssl_certificate": "...",
  }

`Error Responses`:

* ``400 Bad Request`` The request body does not follow the API (one argument is missing or malformed).

* ``402 Payment Required`` The request can not be fullfilled because account is locked.

* ``404 Not Found`` The instance can not be found.

* ``409 Conflict`` The request can not be process because of the current status of the instance

Bang instance
-------------

Trigger the reinstanciation of all partitions in the instance tree

`Request`::

   `POST` http://example.com/api/v1/instance/{instance_id}/bang.{xml|json}

`Route values`:

* ``instance_id``: the ID of the instance

`Expected Request Body`::

  {
    "log": "Explain why this method was called",
  }

`Expected Response`::

  HTTP/1.1 200 OK
  Content-Type: application/json; charset=utf-8
  {
    "status": "updating"
  }

`Error Responses`:

* ``400 Bad Request`` The request body does not follow the API (one argument is missing or malformed).

* ``402 Payment Required`` The request can not be fullfilled because account is locked.

* ``404 Not Found`` The instance can not be found.

* ``202 Accepted`` The request has been accepted for processing::

    {
      "status": "waiting before processing"
    }

Update instance status
----------------------

Update the instance status

`Request`::

   `POST` http://example.com/api/v1/instance/{instance_id}.{xml|json}

`Expected Request Body`::

  {
    "status": "{start,stop,updating,error}",
    "log": "explanation of the status",
  }

`Expected Response`::

  HTTP/1.1 200 OK
  Content-Type: application/json; charset=utf-8
  {
    "status": "started",
  }

`Error Responses`:

* ``400 Bad Request`` The request body does not follow the API (one argument is missing or malformed).

* ``402 Payment Required`` The request can not be fullfilled because account is locked.

* ``409 Conflict`` The request can not be process because of the current status of the instance (sla changed, instance is under deletion, software release can not be changed, ...).

* ``404 Not Found`` The instance can not be found.

Update instance connection
--------------------------

Update the instance connection informations

`Request`::

   `POST` http://example.com/api/v1/instance/{instance_id}/setconnection.{xml|json}

`Expected Request Body`::

  {
    "connection": {
      "custom_connection_parameter_1": "foo",
      "custom_connection_parameter_2": "bar"
    },
  }

`Expected Response`::

  HTTP/1.1 200 OK

`Error Responses`:

* ``400 Bad Request`` The request body does not follow the API (one argument is missing or malformed).

* ``402 Payment Required`` The request can not be fullfilled because account is locked.

* ``409 Conflict`` The request can not be process because of the current status of the instance (sla changed, instance is under deletion, software release can not be changed, ...).

* ``404 Not Found`` The instance can not be found.

Computer Methods
****************

Registering a new computer
--------------------------

Add a new computer in the system.

`Request`::

   `POST` http://example.com/api/v1/computer.{xml|json}

`Expected Request Body`::

  {
    "title": "My unique computer",
  }

`Expected Response`::

  HTTP/1.1 201 Created
  Content-Type: application/json; charset=utf-8
  {
    "computer_id": "COMP-0",
    "ssl_key": "...",
    "ssl_certificate": "...",
    "status": "available"
  }

`Error Responses`:

* ``400 Bad Request`` The request body does not follow the API (one argument is missing or malformed).

* ``402 Payment Required`` The request can not be fullfilled because account is locked.

* ``409 Conflict`` The request can not be process because of the existence of a computer with the same title

* ``202 Accepted`` The request has been accepted for processing::

    {
      "status": "waiting before processing"
    }

Getting computer information
----------------------------

Get the status of a computer

`Request`::

   `GET` http://example.com/api/v1/computer/{computer_id}.{xml|json}

`Route values`:

* ``computer_id``: the ID of the instance

`No Expected Request Body`

`Expected Response`::

  HTTP/1.1 200 OK
  Content-Type: application/json; charset=utf-8
  {
    "computer_id": "COMP-0",
    "status": "available",
    "software": [
      {
        software_release="http://example.com/example.cfg",
        status="install requested",
      },
    ],
    "partition": [
      {
        title="slapart1",
        instance_id="foo",
        status="start requested",
        software_release="http://example.com/example.cfg",
      },
      {
        title="slapart2",
        instance_id="bar",
        status="started",
        software_release="http://example.com/example.cfg",
      },
    ],
  }

`Error Responses`:

* ``400 Bad Request`` The request body does not follow the API (one argument is missing or malformed).

* ``402 Payment Required`` The request can not be fullfilled because account is locked.

* ``404 Not Found`` The computer can not be found.

Modifying computer partition
----------------------------

Modify computer status in the system

`Request`::

   `POST` http://example.com/api/v1/computer/{computer_id}/setpartition.{xml|json}

`Route values`:

* ``computer_id``: the ID of the instance

`Expected Request Body`::

  {
    "partition": [
      {
        "title": "part1",
        "public_ip": "::1",
        "private_ip": "127.0.0.1",
        "tap_interface": "tap2",
      },
    ],
  }

`Expected Response`::

  HTTP/1.1 200 OK
  Content-Type: application/json; charset=utf-8
  {
  }

`Error Responses`:

* ``400 Bad Request`` The request body does not follow the API (one argument is missing or malformed).

* ``402 Payment Required`` The request can not be fullfilled because account is locked.

* ``404 Not Found`` The computer can not be found.

* ``409 Conflict`` The request can not be process because of the existence of a computer with the same title

* ``202 Accepted`` The request has been accepted for processing::

    {
      "status": "waiting before processing"
    }

Supplying new software
----------------------

Request to suply a new software release on a computer

`Request`::

   `POST` http://example.com/api/v1/computer/{computer_id}/supply.{xml|json}

`Route values`:

* ``computer_id``: the ID of the instance

`Expected Request Body`::

  {
    "status": "{requested,updating,available,error,unavailable}",
    "log": "explanation of the status",
  }

`Expected Response`::

  HTTP/1.1 200 OK
  Content-Type: application/json; charset=utf-8
  {
  }

`Error Responses`:

* ``400 Bad Request`` The request body does not follow the API (one argument is missing or malformed).

* ``402 Payment Required`` The request can not be fullfilled because account is locked.

* ``404 Not Found`` The computer can not be found.

* ``409 Conflict`` The request can not be process because of the existence of a computer with the same title

* ``202 Accepted`` The request has been accepted for processing::

    {
      "status": "waiting before processing"
    }

Bang computer
-------------

Request update on all partitions

`Request`::

   `POST` http://example.com/api/v1/computer/{computer_id}/bang.{xml|json}

`Route values`:

* ``computer_id``: the ID of the instance

`Expected Request Body`::

  {
    "log": "Explain why this method was called",
  }

`Expected Response`::

  HTTP/1.1 200 OK
  Content-Type: application/json; charset=utf-8
  {
    "status": "updating"
  }

`Error Responses`:

* ``400 Bad Request`` The request body does not follow the API (one argument is missing or malformed).

* ``402 Payment Required`` The request can not be fullfilled because account is locked.

* ``404 Not Found`` The computer can not be found.

* ``202 Accepted`` The request has been accepted for processing::

    {
      "status": "waiting before processing"
    }

Report usage
------------

Report computer usage

`Request`::

   `POST` http://example.com/api/v1/computer/{computer_id}/report.{xml|json}

`Route values`:

* ``computer_id``: the ID of the instance

`Expected Request Body`::

  {
    "tiosafe": "...",
  }

`Expected Response`::

  HTTP/1.1 200 OK

`Error Responses`:

* ``400 Bad Request`` The request body does not follow the API (one argument is missing or malformed).

* ``402 Payment Required`` The request can not be fullfilled because account is locked.

* ``404 Not Found`` The computer can not be found.
