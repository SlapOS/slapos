
**************************************************************************
This howto is for private networks only, in case the customer is migrating
from a previously installed Maarch.
**************************************************************************


Hot to install Maarch with SlapOS
=================================

 1) Require the right Software Release ({insert SR number/URL here})

 2) Request an instance of that Software Release.
    Since we need to provide a parameter (type=resilient) that is not available through
    the SlapOS web site, it must be done at command line.

    If you are migrating data from an existing Maarch installation:

    2.1) copy a 'data only' SQL dump - no schema - to the server that contains
         the instance. Let's say it is /tmp/data.sql
         The file must be readable by world, because we don't know yet the number
         of the partition that will need to access it.
         Remember to remove it afterwards.

     The command line to request a partition is:

     slapos request /etc/opt/slapos/slapos-client.cfg maarch-instance-name \
            https://lab.nexedi.com/nexedi/slapos/raw/slapos-0.159/software/maarch/software.cfg \
            --type=resilient --configuration maarch-sql-data-file=/tmp/data.sql

     If you are not migrating data, don't provide the maarch-sql-data-file parameter.
     A minimal working database will be created.

 3) deploy the instance.
    You should be able to connect to both Maarch (user 'superadmin')
    and Postgres (user 'postgres') with the (very long)
    passport reported in the connection parameters of the partition 'apache0'.

    NB: even if you copied the SQL data from a previous installation, the 'superadmin' password
        is set from the published connection parameter. If there are other admin accounts,
        their password is not changed.

 4) Again, only if you are migrating:
    connect to the server, inside the partition of type apache-export
    copy the docservers data inside the folders:
        srv/docservers/ai
        srv/docservers/manual
        srv/docservers/OAIS_main
        srv/docservers/OAIS_safe
        srv/docservers/offline
        srv/docservers/templates

    also, change the owner and group of the copied files to the user that owns the partition.

