
LAPP stack
==========

This fork of the LAMP stack provides:

 - a Postgres instance, with an empty database and a 'postgres' superuser.
   Log rotation is handled by Postgres itself.

 - a psycopg2 (postgres driver) egg to be used by further configuration recipes

 - a hook (custom-application-deployment) for configuring the PHP application

