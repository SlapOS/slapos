Proftpd with sftp and virtual users

http://www.proftpd.org/docs/

# Features

 * sftp only is enabled, with authentication by key or password
 * partially uploadloaded are not visible thanks to [`HiddenStores`](http://proftpd.org/docs/directives/linked/config_ref_HiddenStores.html) ( in fact they are, but name starts with `.` )
 * 5 failed login attempts will cause the host to be temporary banned


# TODO

 * log rotation
 * make sure SFTPLog is useful (seems very verbose and does not contain more than stdout)
 * make it easier to manage users ( using `mod_auth_web` against an ERP5 endpoint or accepting a list of user/password as instance parameter )
 * allow configuring webhooks when new file is uploaded
