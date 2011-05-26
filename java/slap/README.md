this is libslap for Java.
More informations at http://www.slapos.org.

Dependencies :
=============

In order to use this library, please also install the following libraries :

jackson-core-asl
jackson-jaxrs
jackson-mapper-asl
jersey-client
jersey-core

You can find those libraries in this archive :
http://download.java.net/maven/2/com/sun/jersey/jersey-archive/1.6/jersey-archive-1.6.zip

Future releases of libslap-java may be provided with Maven pom.

How to use it : 
This library should be used in conjunction with the "rest-json" branch of
libslap-python
(https://gitorious.org/slapos/slapos-libslap-python/commits/rest-json) and with
the "rest" branch of slapproxy 
(https://gitorious.org/slapos/slapos-tool-proxy/commits/rest).

When using slapproxy, a special Buildout profile should be used : 

    [buildout]
    extends =
      https://gitorious.org/slapos/slapos/blobs/raw/master/bootstrap/software.cfg
    
    extensions +=
      mr.developer
    auto-checkout = *
    
    parts +=
      pyflakes
    
    [sources]
    # mr.developer sources definition
    slapos.slap = git http://git.gitorious.org/slapos/slapos-libslap-python.git branch=rest-json
    slapos.tool.proxy = git git@gitorious.org:slapos/slapos-tool-proxy.git branch=rest
    
    [pyflakes]
    recipe = zc.recipe.egg
    scripts =
      pyflakes
    eggs =
      pyflakes
      setuptools
    
    entry-points = pyflakes=pkg_resources:run_script
    arguments = 'pyflakes', 'pyflakes'
    
    [slapos]
    interpreter = python
    eggs +=
    # develop helper eggs
      ipython
      ipdb
      pyflakes
      pep8
      rstctl
    

This profile will install the needed special branches of slapproxy and
libslap-python.

Known bugs :
=============

* Ugly, first implementation of libslap-java from python 
* We should not define a computer when using slap for requesting instances, but
  only to install softwares.
* Implement Destroy for ComputerPartition
* Currently, two separate notions have been interchanged. computer_partition_id
  represents the internal name of the computer partition from the point of view
  of slapgrid. partition_reference is the human name set by the person requesting
  an instance. A bug is preventing us to separate those notions, either in the
  libslap-java or in the slapproxy implementation.


Changelog :
=============

2011/05/20
===
Initial release
(Cedric de Saint Martin)

2011/05/24
===
Slap is no longer a singleton, several instances can be used at the same time with several masters.
(Cedric de Saint Martin)