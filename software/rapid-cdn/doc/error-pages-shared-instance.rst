Error Page Management — Site Owner Guide
=========================================

When your backend is unreachable or returns an error, the CDN returns
an error page to the end user.  You can replace the default pages for
backend-related errors with your own branded HTML.


Connection parameters
---------------------

After your frontend shared instance is deployed you receive an
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

Send a complete HTML document as the request body to::

    PUT UPLOAD_URL/CODE

where ``CODE`` is ``502``, ``503``, or ``504``.

* Request body: a complete HTML document (UTF-8).  Maximum size: 2 MB.
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


Example HTML page
-----------------

The following is a complete, self-contained HTML document you can use
as a starting point.  Replace the company name, colours, and message
with your own branding.

.. code-block:: html

    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>503 — Temporarily Unavailable</title>
      <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body {
          font-family: system-ui, -apple-system, sans-serif;
          background: #fafafa;
          color: #1a202c;
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 100vh;
          padding: 2rem;
        }
        .card {
          background: #fff;
          border-top: 4px solid #3182ce;
          border-radius: 6px;
          box-shadow: 0 1px 8px rgba(0,0,0,.07);
          max-width: 480px;
          width: 100%;
          padding: 2.5rem 2rem;
        }
        .logo {
          font-size: 1.25rem;
          font-weight: 700;
          color: #3182ce;
          margin-bottom: 1.5rem;
        }
        h1 {
          font-size: 1.3rem;
          margin-bottom: .75rem;
        }
        p { color: #4a5568; line-height: 1.65; margin-bottom: .75rem; }
        a { color: #3182ce; }
        .code {
          margin-top: 1.5rem;
          font-size: .75rem;
          color: #a0aec0;
        }
      </style>
    </head>
    <body>
      <div class="card">
        <div class="logo">My Company</div>
        <h1>We&rsquo;ll be right back</h1>
        <p>
          Our service is temporarily unavailable while we perform
          scheduled maintenance.  We apologise for the inconvenience.
        </p>
        <p>
          If you need immediate assistance please contact us at
          <a href="mailto:support@example.com">support@example.com</a>.
        </p>
        <div class="code">HTTP 503 &mdash; Service Unavailable</div>
      </div>
    </body>
    </html>

The same document structure works for codes 502 and 504; adjust the
``<title>``, heading, and body text to describe the specific error.
Save a separate file for each code you want to customise and upload
them individually.


Notes
-----

* Changes propagate to CDN frontend nodes within approximately one
  minute (the frontend error-page-updater polls the EPM on that
  interval and triggers an HAProxy reload when files change).
* Each shared instance has its own independent upload URL and token.
  Your pages only affect your own site.
* The upload URL is stable for the lifetime of the shared instance.
  You do not need to re-upload pages after CDN reconfigurations unless
  you want to change them.
