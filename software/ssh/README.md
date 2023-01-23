If we install this SSH SR in theia, there will be a theia instance, and the SSH SR is "inside" the theia. In this case, when user login through ssh, they will stay at the outer HOME directory(e.g: /srv/slapgrid/slappart1/), aka the HOME directory of theia. Even if we set a customized HOME directory in the authorized key file(/srv/slapgrid/slappart1/srv/runner/slappart2).

This is because the openssh client reads the home directory from/etc/passwd file:
https://github.com/openssh/openssh-portable/blob/2d1ff2b9431393ad99ef496d5e3b9dd0d4f5ac8c/session.c#L1027-L1029
So setting the HOME variable in the key file or export HOME in the sshd service won't work. If we want ssh SR read to the custom HOME directory, we may need further efforts
