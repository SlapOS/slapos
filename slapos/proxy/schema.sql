--version:10
CREATE TABLE IF NOT EXISTS software%(version)s (url VARCHAR(255) UNIQUE);
CREATE TABLE IF NOT EXISTS computer%(version)s (
  address VARCHAR(255),
  netmask VARCHAR(255),
  CONSTRAINT uniq PRIMARY KEY (address, netmask));

CREATE TABLE IF NOT EXISTS partition%(version)s (
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

CREATE TABLE IF NOT EXISTS slave%(version)s (
  reference VARCHAR(255) UNIQUE,
  connection_xml TEXT,
  hosted_by VARCHAR(255),
  asked_by VARCHAR(255) -- only used for debugging,
                        -- slapproxy does not support proper scope
);

CREATE TABLE IF NOT EXISTS partition_network%(version)s (
  partition_reference VARCHAR(255),
  reference VARCHAR(255),
  address VARCHAR(255),
  netmask VARCHAR(255)
);
