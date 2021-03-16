#!/bin/sh
software_name=your_software_name
software_release_uri=~/srv/project/slapos/software/$software_name/software.cfg
slapos supply $software_release_uri slaprunner
slapos request $software_name'_1' $software_release_uri