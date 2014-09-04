-- Real world example of webrunner database running version 10 of proxy db.
PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE software10 (url VARCHAR(255) UNIQUE);
INSERT INTO "software10" VALUES('/srv/slapgrid//srv//runner/project//slapos/software.cfg');
CREATE TABLE computer10 (
  address VARCHAR(255),
  netmask VARCHAR(255),
  CONSTRAINT uniq PRIMARY KEY (address, netmask));
INSERT INTO "computer10" VALUES('127.0.0.1','255.255.255.255');
CREATE TABLE partition10 (
  reference VARCHAR(255) UNIQUE,
  slap_state VARCHAR(255) DEFAULT 'free',
  software_release VARCHAR(255),
  xml TEXT,
  connection_xml TEXT,
  slave_instance_list TEXT,
  software_type VARCHAR(255),
  partition_reference VARCHAR(255),
  requested_by VARCHAR(255), -- only used for debugging,
                             -- slapproxy does not support proper scope
  requested_state VARCHAR(255) NOT NULL DEFAULT 'started'
);
INSERT INTO "partition10" VALUES('slappart0','busy','/srv/slapgrid//srv//runner/project//slapos/software.cfg','<?xml version=''1.0'' encoding=''utf-8''?>
<instance>
  <parameter id="json">{
  "site-id": "erp5"
  }
}</parameter>
</instance>
',NULL,NULL,'production','slapos',NULL,'started');
INSERT INTO "partition10" VALUES('slappart1','busy','/srv/slapgrid//srv//runner/project//slapos/software.cfg','<?xml version=''1.0'' encoding=''utf-8''?>
<instance/>
','<?xml version=''1.0'' encoding=''utf-8''?>
<instance>
  <parameter id="url">mysql://127.0.0.1:45678/erp5</parameter>
</instance>
',NULL,'mariadb','MariaDB DataBase','slappart0','started');
INSERT INTO "partition10" VALUES('slappart2','busy','/srv/slapgrid//srv//runner/project//slapos/software.cfg','<?xml version=''1.0'' encoding=''utf-8''?>
<instance>
  <parameter id="cloudooo-json"></parameter>
</instance>
','<?xml version=''1.0'' encoding=''utf-8''?>
<instance>
  <parameter id="url">cloudooo://127.0.0.1:23000/</parameter>
</instance>
',NULL,'cloudooo','Cloudooo','slappart0','started');
INSERT INTO "partition10" VALUES('slappart3','busy','/srv/slapgrid//srv//runner/project//slapos/software.cfg','<?xml version=''1.0'' encoding=''utf-8''?>
<instance/>
','<?xml version=''1.0'' encoding=''utf-8''?>
<instance>
  <parameter id="url">memcached://127.0.0.1:11000/</parameter>
</instance>
',NULL,'memcached','Memcached','slappart0','started');
INSERT INTO "partition10" VALUES('slappart4','busy','/srv/slapgrid//srv//runner/project//slapos/software.cfg','<?xml version=''1.0'' encoding=''utf-8''?>
<instance/>
','<?xml version=''1.0'' encoding=''utf-8''?>
<instance>
  <parameter id="url">memcached://127.0.0.1:13301/</parameter>
</instance>
',NULL,'kumofs','KumoFS','slappart0','started');
INSERT INTO "partition10" VALUES('slappart5','busy','/srv/slapgrid//srv//runner/project//slapos/software.cfg','<?xml version=''1.0'' encoding=''utf-8''?>
<instance>
  <parameter id="kumofs-url">memcached://127.0.0.1:13301/</parameter>
  <parameter id="memcached-url">memcached://127.0.0.1:11000/</parameter>
  <parameter id="cloudooo-url">cloudooo://127.0.0.1:23000/</parameter>
</instance>
','<?xml version=''1.0'' encoding=''utf-8''?>
<instance>
  <parameter id="url">https://[fc00::1]:10001</parameter>
</instance>
',NULL,'tidstorage','TidStorage','slappart0','started');
INSERT INTO "partition10" VALUES('slappart6','free',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'started');
INSERT INTO "partition10" VALUES('slappart7','free',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'started');
INSERT INTO "partition10" VALUES('slappart8','free',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'started');
INSERT INTO "partition10" VALUES('slappart9','free',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'started');
CREATE TABLE slave10 (
  reference VARCHAR(255) UNIQUE,
  connection_xml TEXT,
  hosted_by VARCHAR(255),
  asked_by VARCHAR(255) -- only used for debugging,
                        -- slapproxy does not support proper scope
);
CREATE TABLE partition_network10 (
  partition_reference VARCHAR(255),
  reference VARCHAR(255),
  address VARCHAR(255),
  netmask VARCHAR(255)
);
INSERT INTO "partition_network10" VALUES('slappart0','slappart0','127.0.0.1','255.255.255.255');
INSERT INTO "partition_network10" VALUES('slappart0','slappart0','fc00::1','ffff:ffff:ffff::');
INSERT INTO "partition_network10" VALUES('slappart1','slappart1','127.0.0.1','255.255.255.255');
INSERT INTO "partition_network10" VALUES('slappart1','slappart1','fc00::1','ffff:ffff:ffff::');
INSERT INTO "partition_network10" VALUES('slappart2','slappart2','127.0.0.1','255.255.255.255');
INSERT INTO "partition_network10" VALUES('slappart2','slappart2','fc00::1','ffff:ffff:ffff::');
INSERT INTO "partition_network10" VALUES('slappart3','slappart3','127.0.0.1','255.255.255.255');
INSERT INTO "partition_network10" VALUES('slappart3','slappart3','fc00::1','ffff:ffff:ffff::');
INSERT INTO "partition_network10" VALUES('slappart4','slappart4','127.0.0.1','255.255.255.255');
INSERT INTO "partition_network10" VALUES('slappart4','slappart4','fc00::1','ffff:ffff:ffff::');
INSERT INTO "partition_network10" VALUES('slappart5','slappart5','127.0.0.1','255.255.255.255');
INSERT INTO "partition_network10" VALUES('slappart5','slappart5','fc00::1','ffff:ffff:ffff::');
INSERT INTO "partition_network10" VALUES('slappart6','slappart6','127.0.0.1','255.255.255.255');
INSERT INTO "partition_network10" VALUES('slappart6','slappart6','fc00::1','ffff:ffff:ffff::');
INSERT INTO "partition_network10" VALUES('slappart7','slappart7','127.0.0.1','255.255.255.255');
INSERT INTO "partition_network10" VALUES('slappart7','slappart7','fc00::1','ffff:ffff:ffff::');
INSERT INTO "partition_network10" VALUES('slappart8','slappart8','127.0.0.1','255.255.255.255');
INSERT INTO "partition_network10" VALUES('slappart8','slappart8','fc00::1','ffff:ffff:ffff::');
INSERT INTO "partition_network10" VALUES('slappart9','slappart9','127.0.0.1','255.255.255.255');
INSERT INTO "partition_network10" VALUES('slappart9','slappart9','fc00::1','ffff:ffff:ffff::');
COMMIT;

