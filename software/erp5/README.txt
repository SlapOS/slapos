TODO: improve

Instance Parameters
===================

Zope Parameters
---------------
Needed by software-type development (default) and zope.

frontend-software-url
~~~~~~~~~~~~~~~~~~~~~
Software URL of an existing frontend.
XXX: meaning should change (or it will go away) in order to be resilient to
software updates - as they are visible at software-url level.
If it is not provided, no frontend will be requested.

frontend-instance-guid
~~~~~~~~~~~~~~~~~~~~~~
GUID of frontend instance.
Not perfect yet: if that instance is replaced, slaves have to be reconfigured.
Mandatory only if frontend-software-url is also provided.
XXX: should be complemented (or replaced) by more flexible and precise
criteria.

frontend-software-type (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Frontend software type as defined by the software relase at
frontend-software-url.

frontend-domain (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~
Domain name frontend must recognise as belonging to this instance.

