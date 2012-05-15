SlapOS Master REST API (v1)
***************************

Authentication
--------------

In order to authenticate into API X509 key/certificate can be used. It is
possible to obtain them from SlapOS Master, like https:///www.vifib.net

As API is going to be used in environments which support TLS communication
channel, but do not, or support is cumbersome, support X509 keys OAuth-2 will
be proposed by library.

Token based authentication
++++++++++++++++++++++++++

In case if client of API does not fulfill X509 authentication it has a chance
to use token based authentication (after obtaining proper token).

Client application HAVE TO use ``"Authorization"`` header, even if OAuth-2
allows other ways (like hvaing token in GET parameter or as form one).
They were not implemented as begin fragile from security point of view.

Example of using Bearer token::

  GET /api/v1/instance/{instance_id} HTTP/1.1
  Host: example.com
  Accept: application/json
  Authorization: Bearer 7Fjfp0ZBr1KtDRbnfVdmIw

Exchange format
---------------

SlapOS master will support both XML and JSON formats for input and output.

The Accept header is required and responsible for format selection.

Response status code
--------------------

Success
+++++++

``GET`` requests will return a ``"200 OK"`` response if the resource is
successfully retrieved. In case if client will set ``"If-Midified-Since"``
header the response could be ``"304 Not Modified"``. Also ``GET`` will return
``"Last-Modified"`` headers.

``POST`` requests which create a resource we will return a ``"201 Created"``
response if successful.

``POST`` requests which perform some other action such as sending a campaign
will return a ``"200 OK"`` response if successful.

``PUT`` requests will return a ``"200 OK"`` response if the resource is
successfully updated and ``"204 No Content"`` in case if no modification was
applied..

``OPTIONS`` requests will return ``"204 No Content"`` response with headers
informing about possible method usage.

Common Error Responses
++++++++++++++++++++++

400 Bad Request
~~~~~~~~~~~~~~~
The request body does not follow the API (one argument is missing or
malformed). The full information is available as text body::

  HTTP/1.1 400 Bad Request
  Content-Type: application/json

  {
    "computer_id": "Parameter is missing"
  }

401 Unauthorized
~~~~~~~~~~~~~~~~

The request is not authorised. The response will contain location to a server
which is capable to provide access credentials.

For servers using Bearer token authentication::

  HTTP/1.1 401 Unauthorized
  WWW-Authenticate: Bearer realm="example.com"
  Location: https://authserv.example.com/path-to-auth

402 Payment Required
~~~~~~~~~~~~~~~~~~~~

The request can not be fulfilled because account is locked.

404 Not Found
~~~~~~~~~~~~~
Request to non existing resource made.

500 Internal Server Error
~~~~~~~~~~~~~~~~~~~~~~~~~
Unexpected error.

Introsepcation Methods
**********************

Fetching list of access urls
----------------------------

Explain acccess points in dictionary.

Client is expected to ask about connection points before doing any request.

In case if required mapping is defined on client side, but server does not
expose this information, it means, that such capability is not available on
server side and should not be used.

In case if client does not support exposed mapping it is allowed to ignore
them.

Client shall be aware that one API can be spanned across many servers and that
all urls are given as abolute ones.

Endpoint to invoke required action is in ``url`` object, where values in
``{}`` shall be replaced with corresponding access urls. For example
``instance_url`` shall be replaced with obtained URL of instance (by request
or list).

``method`` is required method on URL.

All required parameters, if any, are in ``required`` object.

All optional understandable parameters, if any, are in ``optional`` object.

In case if access point requires authentication, then ``authentication`` will be set to ``true``.

`Request`::

  GET / HTTP/1.1
  Host: example.com
  Accept: application/json

`No Expected Request Body`

Extract of possible response::

  HTTP/1.1 200 OK
  Content-Type: application/json; charset=utf-8

  {
    "instance_bang": {
      "authentication": true,
      "url": "{instance_url}/bang",
      "method": "POST",
      "required": {
        "log": "unicode"
      },
      "optional": {}
    },
    "instance_list": {
      "authentication": true,
      "url": "http://three.example.com/instance",
      "method": "GET",
      "required": {},
      "optional": {}
    },
    "register_computer": {
      "authentication": true,
      "url": "http://two.example.com/computer",
      "method": "POST",
      "required": {
        "title": "unicode"
      },
    },
    "request_instance": {
      "authentication": true,
      "url": "http://one.example.com/instance",
      "method": "POST",
      "required": {
         "status": "unicode",
         "slave": "bool",
         "title": "unicode",
         "software_release": "unicode",
         "software_type": "unicode",
         "parameter": "object",
         "sla": "object"
      },
      "optional": {}
    }
  }

All documentation here will refer to named access points except otherwise
stated. The access point will appear in ``[]`` after method name.

Instance Methods
****************

Fetching list of instances
--------------------------

Ask for list of instances.

`Request`::

  GET [instance_list] HTTP/1.1
  Host: example.com
  Accept: application/json

`No Expected Request Body`

`Expected Response`::

  HTTP/1.1 200 OK
  Content-Type: application/json; charset=utf-8

  {
    "list": ["http://one.example.com/one", "http://two.example.com/something"]
  }

`Additional Responses`::

  HTTP/1.1 204 No Content

In case where not instances are available.

Requesting a new instance
-------------------------

Request a new instantiation of a software.

`Request`::

  POST [request_instance] HTTP/1.1
  Host: example.com
  Accept: application/json
  Content-Type: application/json; charset=utf-8

`Expected Request Body`::

  {
    "status": "started",
    "slave": false,
    "title": "My unique instance",
    "software_release": "http://example.com/example.cfg",
    "software_type": "type_provided_by_the_software",
    "parameter": {
      "Custom1": "one string",
      "Custom2": "one float",
      "Custom3": [
        "abc",
        "def"
      ]
    },
    "sla": {
      "computer_id": "COMP-0"
    }
  }

`Expected Response`::

  HTTP/1.1 201 Created
  Content-Type: application/json; charset=utf-8
  Location: http://maybeother.example.com/some/url/instance_id

  {
    "status": "started",
    "connection": {
      "custom_connection_parameter_1": "foo",
      "custom_connection_parameter_2": "bar"
    }
  }

`Additional Responses`::

  HTTP/1.1 202 Accepted
  Content-Type: application/json; charset=utf-8

  {
    "status": "processing"
  }

The request has been accepted for processing

`Error Responses`:

* ``409 Conflict`` The request can not be process because of the current
  status of the instance (sla changed, instance is under deletion, software
  release can not be changed, ...).


Get instance information
------------------------

Request all instance information.

`Request`::

  GET [instance_info] HTTP/1.1
  Host: example.com
  Accept: application/json

`Route values`:

* ``instance_id``: the ID of the instance

`No Expected Request Body`

`Expected Response`::

  HTTP/1.1 200 OK
  Content-Type: application/json; charset=utf-8

  {
    "title": "The Instance Title",
    "status": "start", # one of: start, stop, destroy
    "software_release": "http://example.com/example.cfg",
    "software_type": "type_provided_by_the_software",
    "slave": False, # one of: True, False
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
      "public_ip": ["::1", "91.121.63.94"],
      "private_ip": ["127.0.0.1"],
      "tap_interface": "tap2",
    },
  }

`Error Responses`:

* ``409 Conflict`` The request can not be process because of the current
  status of the instance

Get instance authentication certificates
----------------------------------------

Request the instance certificates.

`Request`::

  GET [instance_certificate] HTTP/1.1
  Host: example.com
  Accept: application/json

`Route values`:

* ``instance_id``: the ID of the instance

`No Expected Request Body`

`Expected Response`::

  HTTP/1.1 200 OK
  Content-Type: application/json; charset=utf-8

  {
    "ssl_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADAN...h2VSZRlSN\n-----END PRIVATE KEY-----",
    "ssl_certificate": "-----BEGIN CERTIFICATE-----\nMIIEAzCCAuugAwIBAgICHQI...ulYdXJabLOeCOA=\n-----END CERTIFICATE-----",
  }

`Error Responses`:

* ``409 Conflict`` The request can not be process because of the current
  status of the instance

Bang instance
-------------

Trigger the re-instantiation of all partitions in the instance tree

`Request`::

  POST [instance_bang] HTTP/1.1
  Host: example.com
  Accept: application/json
  Content-Type: application/json; charset=utf-8

`Route values`:

* ``instance_id``: the ID of the instance

`Expected Request Body`::

  {
    "log": "Explain why this method was called",
  }

`Expected Response`::

  HTTP/1.1 204 No Content

Modifying instance
------------------

Modify the instance information and status.

`Request`::

  PUT [instance_edit] HTTP/1.1
  Host: example.com
  Accept: application/json
  Content-Type: application/json; charset=utf-8

`Expected Request Body`::

  {
    "title": "The New Instance Title",
    "connection": {
      "custom_connection_parameter_1": "foo",
      "custom_connection_parameter_2": "bar"
    }
  }

Where `connection` and `title` are optional.

Setting different.

`Expected Response`::

  HTTP/1.1 200 OK
  Content-Type: application/json; charset=utf-8

  {
    "connection": "Modified",
    "title": "Modified."
  }

`Additional Responses`::

  HTTP/1.1 204 No Content

When nothing was modified.

`Error Responses`:

* ``409 Conflict`` The request can not be process because of the current
  status of the instance (sla changed, instance is under deletion,
  software release can not be changed, ...).

Computer Methods
****************

Registering a new computer
--------------------------

Add a new computer in the system.

`Request`::

  POST [register_computer] HTTP/1.1
  Host: example.com
  Accept: application/json
  Content-Type: application/json; charset=utf-8

`Expected Request Body`::

  {
    "title": "My unique computer",
  }

`Expected Response`::

  HTTP/1.1 201 Created
  Content-Type: application/json; charset=utf-8
  Location: http://maybeother.example.com/some/url/computer_id-0

  {
    "ssl_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADAN...h2VSZRlSN\n-----END PRIVATE KEY-----",
    "ssl_certificate": "-----BEGIN CERTIFICATE-----\nMIIEAzCCAuugAwIBAgICHQI...ulYdXJabLOeCOA=\n-----END CERTIFICATE-----",
  }

`Error Responses`:

* ``409 Conflict`` The request can not be process because of the existence of
  a computer with the same title

Getting computer information
----------------------------

Get the status of a computer

`Request`::

  GET [computer_info] HTTP/1.1
  Host: example.com
  Accept: application/json

`Route values`:

* ``computer_id``: the ID of the computer

`No Expected Request Body`

`Expected Response`::

  HTTP/1.1 200 OK
  Content-Type: application/json; charset=utf-8

  {
    "computer_id": "COMP-0",
    "software": [
      {
        "software_release": "http://example.com/example.cfg",
        "status": "install" # one of: install, uninstall
      },
    ],
    "partition": [
      {
        "title": "slapart1",
        "instance_id": "foo",
        "status": "start", # one of: start, stop, destroy
        "software_release": "http://example.com/example.cfg"
      },
      {
        "title": "slapart2",
        "instance_id": "bar",
        "status": "stop", # one of: start, stop, destroy
        "software_release": "http://example.com/example.cfg"
      },
    ],
  }

Modifying computer
------------------

Modify computer information in the system

`Request`::

  PUT [computer_edit] HTTP/1.1
  Host: example.com
  Accept: application/json
  Content-Type: application/json; charset=utf-8

`Route values`:

* ``computer_id``: the ID of the computer

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
    "software": [
      {
        "software_release": "http://example.com/example.cfg",
        "status": "installed", # one of: installed, uninstalled, error
        "log": "Installation log"
      },
    ],
  }

Where ``partition`` and ``software`` keys are optional, but at least one is
required.

`Expected Response`::

  HTTP/1.1 200 OK
  Content-Type: application/json; charset=utf-8

Supplying new software
----------------------

Request to supply a new software release on a computer

`Request`::

  POST [computer_supply] HTTP/1.1
  Host: example.com
  Accept: application/json
  Content-Type: application/json; charset=utf-8

`Route values`:

* ``computer_id``: the ID of the computer

`Expected Request Body`::

  {
    "software_release": "http://example.com/example.cfg"
  }

`Expected Response`::

  HTTP/1.1 200 OK
  Content-Type: application/json; charset=utf-8

Bang computer
-------------

Request update on all partitions

`Request`::

  POST [computer_bang] HTTP/1.1
  Host: example.com
  Accept: application/json
  Content-Type: application/json; charset=utf-8

`Route values`:

* ``computer_id``: the ID of the computer

`Expected Request Body`::

  {
    "log": "Explain why this method was called",
  }

`Expected Response`::

  HTTP/1.1 204 No Content

Report usage
------------

Report computer usage

`Request`::

  POST [computer_report] HTTP/1.1
  Host: example.com
  Accept: application/json
  Content-Type: application/json; charset=utf-8

`Route values`:

* ``computer_id``: the ID of the computer

`Expected Request Body`::

  {
    "title": "Resource consumptions",
    "start_date": "2011/11/15",
    "stop_date": "2011/11/16",
    "movement": [
      {
        "resource": "CPU Consumption",
        "title": "line 1",
        "reference": "slappart0",
        "quantity": 42.42
      }
    ]
  }

`Expected Response`::

  HTTP/1.1 200 OK
  Content-Type: application/json; charset=utf-8
