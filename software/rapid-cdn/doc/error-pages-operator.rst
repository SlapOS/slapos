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

The HTML you provide is a complete HTML document; the EPM wraps it in
a minimal HTTP/1.0 response that HAProxy requires.  There is no
templating — write plain HTML.  The maximum accepted document size is
2 MB.

Any lines at the very top of the uploaded document that begin with
``#`` are silently dropped before HAProxy framing.  This syntax is
**reserved** for a possible future feature that allows operators to
declare custom response headers; no header support is implemented in
this version.  Treating ``#``-prefix lines as reserved now means files
written today will keep behaving correctly if header support is added
later.


REST API
--------

The same operator URL supports a REST API suitable for automation.

Retrieve current HTML for a code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    GET /operator/TOKEN/CODE

Returns the stored HTML document (``text/html``) or an empty 200
response if no custom page is set for that code.

Example::

    curl --cacert epm.pem \
         https://[2001:db8::1]:24000/operator/TOKEN/503

Upload a custom HTML document
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    PUT /operator/TOKEN/CODE

Request body: a complete HTML document (UTF-8, max 2 MB).
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


Example HTML page
-----------------

The following is a complete, self-contained HTML document suitable for
upload as a custom error page.  Adjust the branding, colours, and text
to match your CDN platform.

.. code-block:: html

    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>503 Service Unavailable</title>
      <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body {
          font-family: system-ui, -apple-system, sans-serif;
          background: #f4f6f9;
          color: #2d3748;
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 100vh;
          padding: 2rem;
        }
        .card {
          background: #fff;
          border-radius: 8px;
          box-shadow: 0 2px 12px rgba(0,0,0,.08);
          max-width: 520px;
          width: 100%;
          padding: 3rem 2.5rem;
          text-align: center;
        }
        .code {
          font-size: 5rem;
          font-weight: 700;
          color: #e53e3e;
          line-height: 1;
        }
        h1 {
          font-size: 1.5rem;
          margin: .75rem 0 1rem;
        }
        p { color: #718096; line-height: 1.6; }
        .footer {
          margin-top: 2rem;
          font-size: .8rem;
          color: #a0aec0;
        }
      </style>
    </head>
    <body>
      <div class="card">
        <div class="code">503</div>
        <h1>Service Unavailable</h1>
        <p>
          We are sorry — the service is temporarily unavailable.
          Our team has been notified and is working to restore it.
          Please try again in a few minutes.
        </p>
        <p class="footer">CDN Platform &mdash; Error reference: 503</p>
      </div>
    </body>
    </html>

The same document structure works for any error code; change the
``<title>``, the ``.code`` text, the ``<h1>``, and the description
paragraph accordingly.  Save separate files for each code you want to
customise and upload them individually.


Multi-language pages with client-side switching
-----------------------------------------------

Because each uploaded page is a complete, self-contained HTML document,
you can ship several languages in the same file and let the visitor's
browser pick the right one with a few lines of inline JavaScript.

The recipe:

1. Wrap each translation in a ``<section data-lang="...">`` block, with
   a matching ``lang=`` attribute for accessibility.
2. Mark one section ``data-default`` — the fallback when nothing else
   matches.
3. CSS hides every ``[data-lang]`` by default and reveals only the one
   tagged ``.active``.
4. A ``<noscript>`` block flips the rule so clients without JavaScript
   see the ``data-default`` section instead of a blank page.
5. A tiny inline script reads ``navigator.languages`` (already sorted
   by browser preference, equivalent to ``Accept-Language`` with
   q-values applied), tries each preference as an exact match and then
   a primary-language fallback (e.g. ``fr-CA`` → ``fr``), and adds
   ``.active`` to the matching section.

The **built-in default pages** bundled with this software release follow
this exact pattern with five languages (English, French, Japanese,
German, Polish) and are the recommended starting point — just
download one and adapt:

* `503.html <../templates/error-pages/503.html>`_ — Service Unavailable
* `502.html <../templates/error-pages/502.html>`_ — Bad Gateway
* `504.html <../templates/error-pages/504.html>`_ — Gateway Timeout
* `500.html <../templates/error-pages/500.html>`_ — Internal Server Error
* `404.html <../templates/error-pages/404.html>`_ — Not Found
* `408.html <../templates/error-pages/408.html>`_ — Request Timeout
* `400.html <../templates/error-pages/400.html>`_ — Bad Request

Add or remove ``<section data-lang="...">`` blocks as needed.  The same
JavaScript handles any number of languages without modification — it
discovers the list from the DOM at runtime.

Keep in mind: HAProxy serves the file via the ``errorfile`` directive,
which loads the whole file into a single buffer.  Rapid.CDN raises
``tune.bufsize`` to **64 KiB** to accommodate multilingual error pages
with comfortable headroom.  If you ship many languages or long
localised copy you should still keep the per-page total under 64 KiB.


Security headers and Content-Security-Policy
--------------------------------------------

The HTTP envelope generated for error files sets ``X-Content-Type-Options:
nosniff`` and an explicit ``Content-Type: text/html; charset=utf-8``;
nothing else security-relevant is added.  In particular, **no
Content-Security-Policy is emitted** for error responses.  Inline
JavaScript and inline CSS in your uploaded pages execute by default,
which is how the built-in multilingual switcher works.

If your cluster deploys a CSP at the HAProxy layer that also applies
to error responses (for example via ``http-after-response set-header
Content-Security-Policy ...``), you have three options:

1. **Allow inline content on error responses.**  The simplest path —
   ``script-src 'unsafe-inline'; style-src 'unsafe-inline'`` on the
   error-response CSP only.  Acceptable because the error-page HTML is
   under your control (either shipped by the operator at SR build time,
   or uploaded by you via PUT), so there is no untrusted-input path.

2. **Allow only the known SHA-256 hashes** of the inline blocks shipped
   in the built-in pages.  These are stable across all seven codes::

       Content-Security-Policy:
         script-src 'sha256-kd4gNDpn2kShafbtEoOkHmUNMKotywb7hR2o4124F88=';
         style-src  'sha256-LHlcrzszQdddVhDnsD/EHYrGUNlsv/Dye8VaQITP9gI='
                    'sha256-46ncLRPYE5GJAkUBe2ZUGES+FfmgO/M1KpwH8fS62iQ='

   The hashes will need updating if you customise the inline script or
   styles in your own uploaded pages — modern browsers print the
   correct value in the developer console when the policy blocks the
   resource.

3. **Compute hashes per upload.**  If you maintain your own custom
   pages, allowlist their hashes the same way.

Avoid the worst-case combination ``script-src 'self'`` (no
``'unsafe-inline'``, no matching ``'sha256-...'``) **with** an inline
``<style>`` block allowed.  In that configuration the CSS will hide
all language sections, the script that would have shown one is blocked,
and the visitor sees a blank page — the ``<noscript>`` fallback does
not engage because the browser does have JavaScript, it just denied
execution.
