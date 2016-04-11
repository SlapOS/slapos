# Host:
# Database: test
# Table: 'computer_partition'
#
CREATE TABLE `computer_partition` (
  `uid` BIGINT UNSIGNED NOT NULL,
  `software_release_url` varchar(255),
  `free_for_request` INT(1),
  `software_type` VARCHAR(255),
  PRIMARY KEY (`uid`, `software_release_url`)
) ENGINE=InnoDB;
