# Slapos egg tests

This software release is used to run unit test of slapos eggs.

The approach is to use setuptools' integrated test runner, `python setup.py test`, to run tests.

The `python` used in this command will be a `zc.recipe.egg` interpreter with
all eggs pre-installed by this software release.

Nexedi staff can see the results of this test from the test suite
`SLAPOS-EGG-TEST` in test result module.


Here's an example session of how a developer could use this software release in
slaprunner to develop a slapos egg, in the example `slapos.core`, to make
changes to the code, run tests and publish changes.

```bash
# install this software release
SR=https://lab.nexedi.com/nexedi/slapos/raw/master/software/slapos-testing/software.cfg 
COMP=slaprunner
slapos supply $SR $COMP
slapos node software
slapos request --node=node=$COMP $SR $COMP
slapos node instance

# The source code is a git clone working copy on the instance
cd ~/srv/runner/instance/slappart0/parts/slapos.core/

# make some changes to the code
vim slapos/tests/client.py

# run tests, using bundled python intepreter with pre-installed eggs dependencies
~/srv/runner/instance/slappart0/software_release/bin/python_for_test setup.py build

# when satified, commit changes
git add -p && git commit

# add developer's fork remote (this is only needed the first time)
git remote add my_remote https://lab.nexedi.com/your_username/slapos.core.git/

# push the changes
git push my_remote HEAD:feature_branch_name

# then submit merge request
```
