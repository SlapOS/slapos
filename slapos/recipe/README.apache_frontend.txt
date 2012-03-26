apache_frontend
==========

Frontend using Apache, allowing to rewrite and proxy URLs like
myinstance.myfrontenddomainname.com to real IP/URL of myinstance.

apache_frontend works using the master instance / slave instance design.
It means that a single main instance of Apache will be used to act as frontend
for many slaves.


How to use
========
First, you will need to request a "master" instance of Apache Frontend with
"domain" parameter, like : 
<?xml version='1.0' encoding='utf-8'?>
<instance>
 <parameter id="domain">moulefrite.com</parameter>
 <parameter id="port">443</parameter>
</instance>

Then, it is possible to request many slave instances
(currently only from slapconsole, UI doesn't work yet)
of Apache Frontend, like : 
instance = request(
       software_release=apache_frontend,
       partition_reference='frontend2',
       shared=True,
       partition_parameter_kw={"url":"https://[1:2:3:4]:1234/someresource"}
     )
Those slave instances will be redirected to the "master" instance,
and you will see on the "master" instance the associated RewriteRules of
all slave instances.

Finally, the slave instance will be accessible from :
https://someidentifier.moulefrite.com.
