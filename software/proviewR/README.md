ProveiwR Software for SlapOS
============================

See at http://www.proview.se/ for source code: https://github.com/siamect/proview

Proview is an Open Source system for process control and automation.

Configure server
================

Mesa component is needed with gbm, which need to install libudev.
On debian/Ubundu you need to run apt-get install libudev-dev if it's not present.


How it works
============

ProviewR can be requested with default software type. Instance will deploy:

- X11 server for graphic display
- XVNC-server is the X VNC (Virtual Network Computing) server. It is based on a standard X server, but it has a "virtual" screen rather than a physical one.
- websockify and NoVNC used for VNC in ordinary browser.
- pwrrt - Proview runtime environment. pwrrt contains the runtime and HMI environment.
- pwrsev - ProviewR Storage Environment. Is installed on storage stations, which contains a database for process history.


ProviewR cannot compile in webrunner because path of software release folder is too long.

Connection parameters
=====================

- url, backend-url: URL of NoVNC which is used for ProviewR Development Environment.
- shell-url, shell-backend: URL for shellinabox, which is a shell session configured for proviewR.

How to use
==========

Open the shell with Shellinabox, use username "proviewr" and password is the monitor password.
Prowier is a desktop application which can be run like chrome or firefox. To start a new projet, type in shellinabox "pwra" then check the NoVNC interface.
Read Getting Started Guide on www.proview.se about how to create and configure a project

Other pwr command are available in the terminal.


TODO
====

 - Make pwrrt Deamon works. For now, it simply refuse to start because some configurations files are missing.
 - Deploy pwrrt and pwrsev in a different partition as it's recommended to not deploy them in the same environment.
 - Fix missing proviewR web and make it works (Also check why some icons are missing on desktop interface).
 - Make proviewR usable in a VNC or another interface tool, fix "Segmentation fault" when opening Proview Ge interface (fix all segmentation fault).
 - Add pwr demo projet to proviewR software so it can be used for demonstration.
 - cleanup and split proviewR component, the component at component/proviewR/buildout.cfg can be split into several other components. 
 - Upgrade proviewR component to the recent version and make it works for SlapOS.


Runtime Environment error
=========================

pwrtt is not starting because of error:

   ProviewR Runtime Environment                                                                                                                          
                                                                                                                                                         
F Could not open file /srv/slapgrid/slappartXX/pwrp/common/load/ld_boot_proviewr_0999.dat                                                                 
F Could not open file /srv/slapgrid/slappartXX/pwrp/common/load/ld_node_proviewr_0999.dat                                                                 
F Cannot find my own node in /srv/slapgrid/slappartXX/pwrp/common/load/ld_node_proviewr_0999.dat 

