# Slapos egg tests

This software release is used to run unit test of slapos eggs.

The approach is to use nxdtest test runner, which will run tests for each
projects, as described in `.nxdtest` file.

The results of this test suite running on Nexedi ERP5 are published as
`SlapOS.Eggs.UnitTest-Master.Python3` and `SlapOS.Eggs.UnitTest-Master.Python2`.


Here's an example session of how a developer could use this software release in
Theia to develop a slapos egg, in the example `slapos.core`, to make
changes to the code, run tests and publish changes.

```bash
# install this software release
SR=https://lab.nexedi.com/nexedi/slapos/raw/1.0/software/slapos-testing/software.cfg
COMP=slaprunner
INSTANCE_NAME=$COMP

slapos supply $SR $COMP
slapos node software
slapos request --node=computer_guid=$COMP $INSTANCE_NAME $SR
slapos node instance

# The path of a an environment script was published by slapos parameters, as
# "environment-script"
slapos request --node=computer_guid=$COMP $INSTANCE_NAME $SR

# sourcing the script in the shell configure all environment variables and
# print a message explaining how to run tests
source ( environment script from step above )

# The source code is a git clone working copy on the instance
cd ~/srv/runner/instance/slappartXXX/parts/slapos.core/

# make some changes to the code
$EDITOR slapos/tests/client.py

# run slapos.core tests
runTestSuite --run slapos.core
# ... or run all eggs tests
runTestSuite

# when satisfied, commit changes
git add -p && git commit

# add developer's fork remote (this is only needed the first time)
git remote add my_remote https://lab.nexedi.com/your_username/slapos.core.git/

# push the changes
git push my_remote HEAD:feature_branch_name

# then submit merge request
```
