SlapOS Master REST API (v1)
***************************

Introduction
------------

This is so called REST interface to Vifib which uses HTTP protocol.

API_BASE
++++++++

``"API_BASE"`` is server side path of the interface. In case of Vifib.net it
is...

Authentication
--------------

In order to authenticate into API X509 key/certificate can be used. It is
possible to obtain them from SlapOS Master, like https:///www.vifib.net

As API is going to be used in environments which support TLS communication
channel, but do not, or support is cumbersome, support X509 keys OAuth-2 will
be proposed by library.

Internal authentication
+++++++++++++++++++++++

**Note**: This authentication mechanism will change. Avoid implementation for now.

In case if client of API does not fulfill X509 authentication it has a chance
to use token based authentication (after obtaining proper token).

Client application HAVE TO use ``"Authorization"`` header, even if OAuth-2
allows other ways (like having token in GET parameter or as form one).
They were not implemented as begin fragile from security point of view.

Example of using Bearer token::

  GET /API_BASE/instance/{instance_id} HTTP/1.1
  Host: example.com
  Accept: application/json
  Authorization: Bearer 7Fjfp0ZBr1KtDRbnfVdmIw


External authentication
+++++++++++++++++++++++

It is possible to use Facebook and Google as Authorization Server with Oauth 2.0
access tokens.  Client shall fetch `access_token` as described in:

 * https://developers.facebook.com/docs/authentication/client-side/ (Facebook)
 * https://developers.google.com/accounts/docs/OAuth2Login (Google)

Such token shall be passed in `Authorization` header, in case of Facebook::

  GET /API_BASE/instance/{instance_id} HTTP/1.1
  Host: example.com
  Accept: application/json
  Authorization: Facebook retrieved_access_token

and in case of Google::

  GET /API_BASE/instance/{instance_id} HTTP/1.1
  Host: example.com
  Accept: application/json
  Authorization: Google retrieved_access_token


The client is responsible for having its own application ID and
configure it that user basic information and email will be available after
using `access_token`, for example by fetching token after query like::

  https://www.facebook.com/dialog/oauth?client_id=FB_ID&response_type=token&redirect_uri=APP_URL&scope=email

While passing access token Vifib.net server will contact proper Authorization
Server (Google or Facebook) and use proper user profile. In case of first time
usage of the service the user will be automatically created, so application
shall be prepared to support HTTP ``"202 Accepted"`` code, as described in `Response status code`_.

Facebook notes
~~~~~~~~~~~~~~

While requesting Facebook access token it is required to set ``scope`` value
to ``email``.

Vifib.net will use those data to create users.

Google notes
~~~~~~~~~~~~

While requesting Google access token it is required to set ``scope`` value
to ``https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email``.

Vifib.net will use those data to create users.

Exchange format
---------------

SlapOS master will support both XML and JSON formats for input and output.

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

``"202 Accepted"`` with json response with status can be returned in order to
indicate that request was correct, but some asynchronous opertions are disallow
to finish it, for example user being in creation process::

  HTTP/1.1 202 Accepted
  Content-Type: application/json; charset=utf-8

  {
    "status": "User under creation."
  }

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

Account Methods
***************

Requesting a new account
------------------------

Add a new user account.

`Request`::

  POST http://example.com/api/v1/account HTTP/1.1
  Content-Type: application/json; charset=utf-8

`Expected Request Body`::

  {
    "first_name": "First Name",
    "last_name": "Last Name",
    "login": "login", # XXX email is perhaps enough?
    "email": "email@example.org",
    "password": "one password",
    "organisation": "ORG", # optional
    "phone_number": "0323232", # optional
    "address": "address",
    "postal_code": "21232",
    "city": "Tokyo"
  }

`Expected Response`::

  HTTP/1.1 201 Created
  Content-Type: application/json; charset=utf-8

  {
    "ssl_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADAN...h2VSZRlSN\n-----END PRIVATE KEY-----",
    "ssl_certificate": "-----BEGIN CERTIFICATE-----\nMIIEAzCCAuugAwIBAgICHQI...ulYdXJabLOeCOA=\n-----END CERTIFICATE-----",
  }

`Error Responses`:

* ``409 Conflict`` The request can not be process because of the existence of an account with the same login or email

Instance Methods
****************

Fetching list of instances
--------------------------

Ask for list of instances.

`Request`::

  GET /API_BASE/instance HTTP/1.1
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

  POST /API_BASE/instance HTTP/1.1
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

  GET /API_BASE/<instance_path> HTTP/1.1
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

  GET /API_BASE/<instance_path>/certificate HTTP/1.1
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

  POST /API_BASE/<instance_path>/bang HTTP/1.1
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

  PUT /API_BASE/<instance_path> HTTP/1.1
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

  POST /API_BASE/computer HTTP/1.1
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

  GET /API_BASE/<computer_path> HTTP/1.1
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

  PUT /API_BASE/<computer_path> HTTP/1.1
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

  HTTP/1.1 204 No Content

Supplying new software
----------------------

Request to supply a new software release on a computer

`Request`::

  POST /API_BASE/<computer_path>/supply HTTP/1.1
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

  POST /API_BASE/<computer_path>/bang HTTP/1.1
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

  POST /API_BASE/<computer_path>/report HTTP/1.1
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
