
LAPP stack
==========

This fork of the LAMP stack provides:

 - a Postgres instance, with an empty database and a 'postgres' superuser.
   Log rotation is handled by Postgres itself.

 - symlinks to all the postgres binaries, usable through unix socket
   with no further authentication, or through ipv6

 - a psycopg2 (postgres driver) egg

 - a hook (custom-application-deployment) for configuring the PHP application

