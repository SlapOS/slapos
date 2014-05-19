slaprunner
==========

Introduction
------------

This software release is used to deploy Slaprunner instances.
Slaprunner is an all-in-one IDE used to develop and test profiles and recipes for SlapOS.

Parameters
----------

user-authorized-key
~~~~~~~~~~~~~~

You need to specify your SSH public key in order to connect to the SSH server of this instance.

Example of parameter XML::

  <?xml version="1.0" encoding="utf-8"?>
  <instance>
  <parameter id="user-authorized-key">ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCdNp7qZMVAzNc07opHshiIFDmJpYXQpetfcSgUj39a409d42PpsJElp7WsAE/x0nN6gUIoWIl7UiAlMzf6bKEJGJVSOZEPTmiJVlgK1Gp+kE0x9yNcncYg7p38Jny0daVA/NkkpAFyRsAm5kLGzyLtaCcktSvy0cJuy7WSSHU05pd1f8Y8thofE9g5t+/JA2VZvipxPkRfkFAG3aOAGLULlTImTSDFSDFGSDFG5F6mMnl7yvY2d6vEHVBu+K+aKmAwZVfCUwtSpa/tq3i2Lppjrw3UfrxbQSFHZCkzefr+u+l4YYe+tJrX7rYJYXD7LIfZfdSeFTlHFaN/yI1 user@host.local</parameter>
  </instance>

instance-amount
~~~~~~~~~~~~~~~

Optional parameter.

Default: 10


Public-directory
----------------
You can serve static files with the webrunner. For that, just put your data in "srv/runner/public". All these files will be served throught the url of the webrunner + "/public/". Useful for developping your own static website.


AUTO-DEPLOYMENT
---------------

for software
~~~~~~~~~~~~

You can automatically deploy a software release while deploying the webrunner itself, using the paramater XML.

To do this, you only need to pass as a parameter named "slapos-software" : "AAA/BBB", where AAA is the folder of slapos.git where is located your BBB software.
For example, to deploy the hello-world software, you need to pass : software/helloworld

This is possible because the slapos.git is automatically downloaded when the webrunner is deployed.

It is also possible to download you own git repository, by providing the url in the "slapos-repository" parameter.

Last but not least, it is also possible to switch the branch with the parameter "slapos-reference" (by default pointing on master)

for instance
~~~~~~~~~~~~

The parameter "auto-deploy-instance" can be explicitly set to allow or prevent the runner to deploy the instance at START TIME (if you manually restart the runner, or if the server reboots). Values : "true" or "false". Default value is "true", except for the instances of import (while type is resilient or test) which is "false"

There also exists the parameter "autorun", which will build&run your software if set to true. For this, you need "auto_deploy" to true, and set the parameter "slapos-software" to the software you want to deploy. Do not hesitate to clone a different repo than "slapos", or to change the tag/branch to use your custom Software Release. (see "slapos-repository" and "slapos-reference" in previous section).

To deploy the instance with some parameters, just give to the runner parameters starting with "parameter-", they will be correctly forwarded to the instance, which will use them for its configuration. For example, if you want to send to the sofware helloworld the parameter "name" with the value "nicolas", here is how to configure the parameter.xml of the webrunner for auto-depolyment :

<?xml version='1.0' encoding='utf-8'?>
<instance>
<parameter id="slapos-software">software/helloworld</parameter>
<parameter id="auto_deploy">true</parameter>
<parameter id="autorun">true</parameter>
<parameter id="parameter-name">nicolas</parameter>
</instance>

Resilience :
------------

To order a resilient runner, you have to request a runner with the option: "--type resilient"

You can then decide on which node you want to deploy each instance, with the parameters.xml :
	<?xml version='1.0' encoding='utf-8'?>
	<instance>
	  <parameter id="-sla-runner2-computer_guid">COMP-XXXX</parameter>
	  <parameter id="-sla-pbs2-computer_guid">COMP-XXXX</parameter>
	  <parameter id="-sla-pbs1-computer_guid">COMP-XXXX</parameter>
	  <parameter id="-sla-runner1-computer_guid">COMP-XXXX</parameter>
	  <parameter id="-sla-runner0-computer_guid">COMP-XXXX</parameter>
	</instance>

If you want to check by yourself that the pull-backup instances do their job, you can change directory to the slappart of runner0, and run ./bin/exporter (after creating your account, using the given backend_url or url): it would fill ./srv/backup/runner with data. If you then go to an import instance (runner1 or runner2) on the port 50005, you should be able to sign in the runner.


Tips :
~~~~~

To find in which partition the instance has been deployed, you can open the page of this specific instance, and look for "slappartXX" on the page.

Tests :
-------

To test the runner, start by ordering a runner with default type. Then READ the important note below :

/!\ IMPORTANT NOTE ON THE TESTS /!\ : in order to make them work, you have to comment the last line of the file __init__.py in the runner module (which is just : "run()"). Indeed, this line is used to load the config, when importing this module throught Gunicorn (the wsgi server). But the test suite loads itself the configuration, in fonction of the tested scenarios, etc... (You can find the module in the SR folder directory, under ./eggs/slapos.toolbox, or under parts/slapos.toolbox if you have a development version)

Then, su in the concerned slapuserX and run "./bin/runTestSuite".

For the tests on the resiliency of the webrunner, please refer to the README in slapos.toolbox.git/slapos/resiliencytest

Request custom frontend :
-------------------------

While deploying a server in your instance, you may need to ask for a custom ipv4 frontend.

The way to do that is to send a new parameter to your runner instance, using the parameters XML. The name of it is "custom-frontend-backend-url".

To create the frontend, you now have to wait the slaprunner to be processed.

You can define the type of your backend using "custom-frontend-backend-type". eg: zope

If you deploy a server, which uses basic auth, you also have to declare the parameter "custom-frontend-basic-auth" as true, or your slaprunner instance won't show as correctly instanciated.

Example :
	<?xml version='1.0' encoding='utf-8'?>
	<instance>
	<parameter id="custom-frontend-backend-url">http(s)://[THE_IPV6_ADDRESS]:PORT</parameter>
	<parameter id="custom-frontend-backend-type">zope</parameter>
	<parameter id="custom-frontend-basic-auth">true</parameter>
	</instance>

Git repositories :
------------------

It is easy to give access to your git repository/ies to everyone, or to clone it on your own computer. For this, there are 2 urls to remember:
  - For read only, you can clone : https://[IPV6]:PORT/git-public/YourRepo.git/
  - For read and write access, using your runner account : https://[IPV6]:PORT/git/YourRepo.git/

To create the repo, go in the folder srv/runner/project and initiate a new git repo (git init/clone --bare XXX).

For the moment, the PORT is the port of monitoring, which is 9685.

Things to notice for the nex developer :
----------------------------------------

As you can see in instance-runner-*.cfg, the buildout section extends a hard-coded template file. If one day you need to modify the filename, do not forget to modify it in instance.cfg, but also in these files ! (the problem is that the content of instance.cfg is not known by buildout while the deployment of the software release)


List of ports used by the webrunner:
------------------------------------
8602 : slapproxy, while running tests
8080 : shellinabox
9684 : apache (monitoring of slaprunner, git access)
22222 : dropbear
50000 : slapproxy
50005 : webrunner (flask app), webdav access

Tips:
-----
You can use shellinabox in fullscreen, by accessing : https://[IPV6]:8080
