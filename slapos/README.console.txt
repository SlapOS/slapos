console
=======

The slapconsole tool allows to interact with a SlapOS Master throught the SLAP
library.

For more information about SlapOS or slapconsole usages, please go to 
http://www.slapos.org.

The slapconsole tool is only a bare Python console with several global variables
defined and initialized.


Initialization and configuration file
=====
Slapconsole allows to automatically connect to a Master using URL and SSL
certificate from given slapos.cfg.
Certificate has to be *USER* certificate, manually obtained from SlapOS master
web interface.

Slapconsole tools reads the given slapos.cfg configuration file and use the
following informations : 
 * Master URL is read from [slapos] in the "master_url" parameter.
 * SSL Certificate is read from [slapconsole] in the "cert_file" parameter.
 * SSL Key is read from [slapconsole] in the "key_file" parameter.

See slapos.cfg.example for examples.


Global functions
=====
 * request() is a shorthand for slap.registerOpenOrder().request() allowing
   to request instances.
 * supply() is a shorthand for slap.registerSupply().supply() allowing to
   request software installation.

For more information about those methods, please read the SLAP library
documentation.


Global aliases
=====
"software_list" is a list containing all the Software Release URLs defined in
client slapos.cfg configuration file.

Also, each Software Release defined in this configuration file is translated
into a global variable to ease the request of those Sofware Releases.

This allows to request instances in a few words, i.e
request("http://www.url.com/path/to/kvm/software.cfg", "mykvm")
can be simplified into : 
request(kvm, "mykvm")
If the slapos.cfg file contains : 
alias = 
  kvm http://www.url.com/path/to/kvm/software.cfg


Global objects
=====
"slap" is an instance of the SLAP library. It is only used for advanced usages.
"slap" instance is obtained by doing : 
slap = slapos.slap.slap()
slap.initializeConnection(config.master_url,
    key_file=config.key_file, cert_file=config.cert_file)
    

Examples
=====
  >>> # Request instance
  >>> request(kvm, "myuniquekvm")

  >>> # Request instance on specific computer
  >>> request(kvm, "myotheruniquekvm",
    filter_kw={ "computer_guid": "COMP-12345" })
  
  >>> # Request instance, specifying parameters (here nbd_ip and nbd_port)
  >>> request(kvm, "mythirduniquekvm",
    partition_parameter_kw={"nbd_ip":"2a01:e35:2e27:460:e2cb:4eff:fed9:48dc", 
    "nbd_port":"1024"})

  >>> # Request software installation on owned computer
  >>> supply(kvm, "mycomputer")

  >>> # Fetch existing instance status
  >>> request(kvm, "myuniquekvm").getState()

  >>> # Fetch instance informations on already launched instance
  >>> request(kvm, "myuniquekvm").getConnectionParameter("url")
