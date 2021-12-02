Proftpd with sftp and virtual users

http://www.proftpd.org/docs/

# Features

 * sftp only is enabled, with authentication by key or password
 * partially uploadloaded are not visible thanks to [`HiddenStores`](http://proftpd.org/docs/directives/linked/config_ref_HiddenStores.html) ( in fact they are, but name starts with `.` )
 * 5 failed login attempts will cause the host to be temporary banned
 * support authentication against an external web service


# TODO

 * make sure SFTPLog is useful (seems very verbose and does not contain more than stdout)
 * allow configuring webhooks when new file is uploaded
