generic_varnish
===============

This recipe creates a varnish instance dedicated for ERP5 with a web checker[1]
set up.

How to Use
==========

On slap console, you can instanciate varnish like this:

instance = request(
  software_type='varnish',
  partition_parameter_kw={
     'backend-url':'https://[your_backend_address]:your_backend_port',
     'web-checker-frontend-url':'http://www.example.com',
     'web-checker-mail-address':'web-checker-result@example.com',
     'web-checker-smtp-host':'mail.example.com',
  }
)

backend-url is the backend url that varnish will cache.

web-checker-frontend-url is the entry-point-url that web checker will check
the HTTP headers of all the pages in the web site.

web-checker-mail-address is the email address where web checker will send
the HTTP Cache cheking result.

web-checker-smtp-host is the smtp server to be used to send the web checker
result.

[Note]
When web-checker-* parameters are not given, web_checker will be disabled.

TODO
====

We need to merge this and apache_frontend recipe.

References
==========

[1] web_checker (it is a part of erp5.util)
http://pypi.python.org/pypi/erp5.util
web_checker: Web site HTTP Cache header checking tool

