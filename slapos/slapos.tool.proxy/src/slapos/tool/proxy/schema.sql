--version:7
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
  software_type VARCHAR(255),
  partition_reference VARCHAR(255),
  requested_by VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS partition_network%(version)s (
  partition_reference VARCHAR(255),
  reference VARCHAR(255),
  address VARCHAR(255),
  netmask VARCHAR(255)
);
