# -*- coding: utf-8 -*-

import pkg_resources

DB_VERSION = pkg_resources.resource_stream('slapos.proxy', 'schema.sql').readline().strip().split(':')[1]

