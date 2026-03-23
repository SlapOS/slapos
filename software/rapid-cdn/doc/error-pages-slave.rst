Error Page Management — Site Owner Guide
=========================================

When your backend is unreachable or returns an error, the CDN returns
an error page to the end user.  You can replace the default pages for
backend-related errors with your own branded HTML.


Connection parameters
---------------------

After your frontend slave is deployed you receive an
``error-page-upload-url`` connection parameter.  This URL already
contains your authentication token in the path::

    error-page-upload-url = https://[2001:db8::1]:24000/slave/TOKEN/

Keep this URL private — it grants write access to your site's error
pages.

The EPM uses a **self-signed TLS certificate**.  The certificate PEM is
available as ``error-page-certificate`` in your instance connection
parameters.  Pass it to curl with ``--cacert``, or use ``-k`` /
``--insecure`` for quick testing.


Which error codes you can customise
------------------------------------

Site owners may only customise backend-related error codes:

======  ==========================  =============================================
Code    Reason                      When it appears
======  ==========================  =============================================
502     Bad Gateway                 Your backend returned an invalid response
503     Service Unavailable         No healthy backend is available right now
504     Gateway Timeout             Your backend did not respond in time
======  ==========================  =============================================

CDN-internal errors (400, 404, 408, 500) are not customisable by site owners.
The 404 page is shown when a request arrives for an address not served by
this CDN at all; it is managed at the operator level only.


Uploading a custom error page
------------------------------

Send the HTML body as the request body to::

    PUT UPLOAD_URL/CODE

where ``CODE`` is ``502``, ``503``, or ``504``.

* Request body: plain HTML (UTF-8).  Maximum size: 2 MB.
* Response: ``204 No Content`` on success.
* The change takes effect immediately — no action needed on your side.

Examples::

    # Upload a custom 503 page
    curl --cacert epm.pem -X PUT \
         -H 'Content-Type: text/html' \
         --data-binary @my-503.html \
         "https://[2001:db8::1]:24000/slave/TOKEN/503"

    # Quick test ignoring the self-signed certificate
    curl -k -X PUT \
         -H 'Content-Type: text/html' \
         --data-binary @my-503.html \
         "https://[2001:db8::1]:24000/slave/TOKEN/503"

The HTML you provide is used as the complete page body.  Write normal
HTML — there is no templating.


Resetting to the operator default
-----------------------------------

To remove your custom page and fall back to the operator's default::

    DELETE UPLOAD_URL/CODE

Response: ``204 No Content``.

Example::

    curl --cacert epm.pem -X DELETE \
         "https://[2001:db8::1]:24000/slave/TOKEN/503"


Override precedence
-------------------

Your custom page takes precedence over the operator's page.  If you
delete your override the operator's page (or the built-in default if the
operator has not set one) is shown instead.


Notes
-----

* Changes propagate to CDN frontend nodes within approximately one
  minute (the frontend error-page-updater polls the EPM on that
  interval and triggers an HAProxy reload when files change).
* Each slave has its own independent upload URL and token.  Your pages
  only affect your own site.
* The upload URL is stable for the lifetime of the slave instance.  You
  do not need to re-upload pages after CDN reconfigurations unless you
  want to change them.
