slapos.manager
==============

Manager is a plugin-like class that is being run in multiple phases of slapos node lifecycle.

-  **format**, manager can format additionally the underlaying OS 
-  **software**, manager can react on software installation
-  **instance**, manager can update instance runtime frequently

Constructor will receive configuration of current stage. Then each method receives
object most related to the current operation. For details see <slapos/manager/interface.py>.

In code, a list of manager instances can be easily retreived by

    from slapos import manager
    manager_list = manager.from_config(config)

Where `from_config` extracts "manager_list" item from dict-like `config` argument
and then dynamically loads modules named according to the configuration inside
`slapos.manager` package. The manager must be a class named Manager and implementing
interface `slapos.manager.interface.IManager`.

Managers might require a list of user for whom they are allowed to perform tasks.
This list of users is given by "power_user_list" in [slapos] section in the
config file.
