slapos.manager
==============

Manager is a plugin-like class that is being run in multiple phases of slapos node lifecycle.

-  **format**, manager can format additionally the underlaying OS 
-  **software**, manager can react on software installation
-  **instance**, manager can update instance runtime frequently

Constructor will receive configuration of current stage. Then each method receives
object most related to the current operation. For details see <slapos/manager/interface.py>.

