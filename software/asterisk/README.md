# OpenSSH server

An OpenSSH server instance in a SlapOS instance. This can be used to access a shell on  this partition or to do ports redirections.

## Known issues

If we create an instance of this SSH Software Release in theia, there will be a theia instance, and the SSH instance is "inside" the theia. In this case, when user login through ssh, they will stay at the outer HOME directory(e.g: /srv/slapgrid/slappart1/), aka the HOME directory of theia. Even if we set a customized HOME directory in the authorized key file(/srv/slapgrid/slappart1/srv/runner/instance/slappart2).

This is because the OpenSSH server reads the home directory from `/etc/passwd` file:
https://github.com/openssh/openssh-portable/blob/2d1ff2b9431393ad99ef496d5e3b9dd0d4f5ac8c/session.c#L1027-L1029

So setting the `HOME` variable in the key file or exporting `HOME` in the sshd service won't work. If we want ssh instance to spawn a shell in the actual `HOME` directory of the partition in case of nested partition, we would need further efforts, for example something like what was done in slaprunner ( [here](https://lab.nexedi.com/nexedi/slapos/blob/686adec3a2526fc54111866cd64de74fb8a4bd29/software/slaprunner/instance-runner.cfg#L270) and [](https://lab.nexedi.com/nexedi/slapos/blob/686adec3a2526fc54111866cd64de74fb8a4bd29/software/slaprunner/template/bash_profile.in#L6-8) )

