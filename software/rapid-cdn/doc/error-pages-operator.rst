Error Page Management — Operator Guide
=======================================

The Error Page Manager (EPM) lets the CDN operator customise the HTML
pages returned to end users when the CDN itself generates an error
response.  Operator-defined pages become the default for every hosted
site; individual site owners can further override the pages for their
own backend errors (see ``error-pages-shared-instance.rst``).


Connection parameters
---------------------

After the instance is deployed the master partition publishes
``error-page-manager-operator-url``.  This URL already contains the
authentication token in the path and gives full access to the management
interface::

    error-page-manager-operator-url = https://[2001:db8::1]:24000/operator/TOKEN/

Keep this URL private — anyone who has it can modify all error pages.

The EPM uses a **self-signed TLS certificate**.  The certificate PEM is
published as ``error-page-certificate`` in the instance connection
parameters so you can pin it explicitly.  When using curl pass it with
``--cacert``, or use ``-k`` / ``--insecure`` for quick testing.


Supported error codes
---------------------

The operator can customise the following codes:

======  ==========================  ============================================
Code    Reason                      When it appears
======  ==========================  ============================================
400     Bad Request                 Malformed HTTP request received by the CDN
404     Not Found                   Request for an address not served by this CDN
408     Request Timeout             Client did not send a complete request in time
500     Internal Server Error       Unexpected error inside the CDN
502     Bad Gateway                 Backend returned an invalid response
503     Service Unavailable         No healthy backend available
504     Gateway Timeout             Backend did not respond in time
======  ==========================  ============================================

Codes 400, 404, 408, and 500 are CDN-internal errors.  Site owners cannot
override them.  Codes 502, 503, and 504 relate to backend availability;
site owners may override those for their own sites.


Web management interface
------------------------

Open the operator URL in a browser.  The page shows one row per error
code with a text area for the HTML body and two buttons:

* **Save** — stores the HTML and immediately regenerates the HAProxy
  error files served to CDN users.
* **Reset** — removes the custom page; the CDN falls back to the
  built-in default page.

The HTML you provide is the ``<body>`` content only; the EPM wraps it in
a minimal HTTP/1.0 response that HAProxy requires.  There is no
templating — write plain HTML.  The maximum accepted body size is 2 MB.


REST API
--------

The same operator URL supports a REST API suitable for automation.

Retrieve current HTML for a code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    GET /operator/TOKEN/CODE

Returns the stored HTML body (``text/html``) or an empty 200 response if
no custom page is set for that code.

Example::

    curl --cacert epm.pem \
         https://[2001:db8::1]:24000/operator/TOKEN/503

Upload a custom HTML body
~~~~~~~~~~~~~~~~~~~~~~~~~

::

    PUT /operator/TOKEN/CODE

Request body: plain HTML (UTF-8, max 2 MB).
Response: ``204 No Content`` on success.

The change is applied immediately — no restart is needed.

Example::

    curl --cacert epm.pem -X PUT \
         -H 'Content-Type: text/html' \
         --data-binary @my-503.html \
         https://[2001:db8::1]:24000/operator/TOKEN/503

Reset to built-in default
~~~~~~~~~~~~~~~~~~~~~~~~~

::

    DELETE /operator/TOKEN/CODE

Response: ``204 No Content``.  The built-in page is restored for the
given code and for every site that had not set its own override.

Example::

    curl --cacert epm.pem -X DELETE \
         https://[2001:db8::1]:24000/operator/TOKEN/503


Override precedence
-------------------

For each error code and each hosted site the page shown to end users is
chosen as follows:

1. Site-owner override for that site (if set)
2. Operator custom page (if set)
3. Built-in default page

Uploading a new operator page immediately re-generates the HAProxy error
files for all sites that do **not** have their own override, so the
change propagates to end users at the next HAProxy configuration reload
on every frontend node (typically within one minute).


Built-in default pages
----------------------

The software release ships default pages for all seven supported codes.
They are minimal, brand-neutral HTML pages that identify the error code
and a brief human-readable description.  Reset any code to restore them.
