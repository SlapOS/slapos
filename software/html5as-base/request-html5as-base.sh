software_name=html5as-base
software_release_uri=~/srv/project/slapos/software/$software_name/software.cfg
slapos supply $software_release_uri slaprunner
slapos request $software_name'_1' $software_release_uri --parameters \ title='John Doe' \
download_url='https://lab.nexedi.com/nexedi/converse.js/-/archive/nexedi-v4.2.0/converse.js-nexedi-v4.2.0.tar.gz'
port=8086