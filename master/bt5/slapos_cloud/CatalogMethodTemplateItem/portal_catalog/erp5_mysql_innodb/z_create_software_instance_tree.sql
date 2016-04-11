# Host:
# Database: test
# Table: 'software_instance_tree'
#
CREATE TABLE `software_instance_tree` (
  `uid` BIGINT UNSIGNED NOT NULL,
  `root_uid` BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (`uid`, `root_uid`)
) ENGINE=InnoDB;
