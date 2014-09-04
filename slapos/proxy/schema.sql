--version:11
CREATE TABLE IF NOT EXISTS software%(version)s (
  url VARCHAR(255),
  computer_reference VARCHAR(255) DEFAULT '%(computer)s',
  CONSTRAINT uniq PRIMARY KEY (url, computer_reference)
);

CREATE TABLE IF NOT EXISTS computer%(version)s (
  reference VARCHAR(255) DEFAULT '%(computer)s',
  address VARCHAR(255),
  netmask VARCHAR(255),
  CONSTRAINT uniq PRIMARY KEY (reference)
);

CREATE TABLE IF NOT EXISTS partition%(version)s (
  reference VARCHAR(255),
  computer_reference VARCHAR(255) DEFAULT '%(computer)s',
  slap_state VARCHAR(255) DEFAULT 'free',
  software_release VARCHAR(255),
  xml TEXT,
  connection_xml TEXT,
  slave_instance_list TEXT,
  software_type VARCHAR(255),
  partition_reference VARCHAR(255), -- name of the instance
  requested_by VARCHAR(255), -- only used for debugging,
                             -- slapproxy does not support proper scope
  requested_state VARCHAR(255) NOT NULL DEFAULT 'started',
  CONSTRAINT uniq PRIMARY KEY (reference, computer_reference)
);

CREATE TABLE IF NOT EXISTS slave%(version)s (
  reference VARCHAR(255), -- unique slave reference
  computer_reference VARCHAR(255) DEFAULT '%(computer)s',
  connection_xml TEXT,
  hosted_by VARCHAR(255),
  asked_by VARCHAR(255) -- only used for debugging,
                        -- slapproxy does not support proper scope
);

CREATE TABLE IF NOT EXISTS partition_network%(version)s (
  partition_reference VARCHAR(255),
  computer_reference VARCHAR(255) DEFAULT '%(computer)s',
  reference VARCHAR(255),
  address VARCHAR(255),
  netmask VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS forwarded_partition_request%(version)s (
  partition_reference VARCHAR(255), -- a.k.a source_instance_id
  master_url VARCHAR(255)
);
