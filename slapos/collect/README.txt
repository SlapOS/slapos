

Collecting Data
================

The "slapos node collect" command collects data from a computer taking a 
few snapshot on different scopes and storing it (currently on sqllite3). 

Scopes of Snapshots are:

  - User Processes: Collects data from all user's process related to SlapOS (ie.: slapuser*)
  - System Information: Collects data from the System Usage and Computer Hardware.

So on every slapos node collect calls (perfomed by cron on every minute), the 
slapos stores the all snapshots for future analizes.

User's Processes Snapshot
==========================

Collect command search for all process launched by all users related to the 
slapos [1]. After this, for each process it uses psutil (or similars tools) to 
collect all available information for every process pid [2].

Once Collected, every Process information is stored on sqllite3 [3], in other 
words, we have 1 line per pid for a giving time. It's used pid number and 
process creation date for create a UID for the process, and it is omitted the 
command name in order to annonymalize the data (so the risk of information 
leak is reduced).

The measuring of process only consider CPU, memory and io operations (rw and 
cycles), we are studying how to measure network (without be intrusive).

System Information Snapshot
============================

Those snapshots has 2 different goals, first is collect current load from existing 
computer (cpu, memory, disk, network...) and the second goal is collect the 
available resources the computer has installed [4]. 

We use 3 types of snapshots for determinate the load and the available resources
(all mostly use psutils to collect data):

  - System Snapshot [5]:  It collects general computer usage like CPU, Memory 
                          and Network IO usage.
                          
  - Computer Snapshot [6]: It collects for now number of CPU cores and available 
                           memory, however we wish to collect more details.
                           
  - Disk Snapshot [7]: It collects the informations related to the a disk 
                        (1 snapshot per disk), which contains total, usage and 
                        io informations.
                        
                        
"Real-time" Partial dump (Dygraph)
===================================

On every run, we dump data from the current day on csv [8] (2 axes), in order to
plot easily with dygraph, so there will be few files available like this:

 - system_cpu_percent.csv
 - system_disk_memory_free__dev_sda1.csv
 - system_disk_memory_free__dev_sdb1.csv
 - system_disk_memory_used__dev_sda1.csv
 - system_disk_memory_used__dev_sdb1.csv
 - system_loadavg.csv
 - system_memory_free.csv
 - system_memory_used.csv
 - system_net_in_bytes.csv
 - system_net_in_dropped.csv
 - system_net_in_errors.csv
 - system_net_out_bytes.csv
 - system_net_out_dropped.csv
 - system_net_out_errors.csv

All contains only information from computer usage, for global usage (for now). It 
is perfectly acceptable keep a realtime copy in csv of the most recently data.

Logrotate
=========

Slapos collects contains its on log rotating policy [9] and gargabe collection [10]. 

  - We dump in folders YYYY-MM-DD, all data which are not from the current day.
  - Every table generates 1 csv with the date from the dumped day.
  - All dumped data is marked as reported on sqllite (column reported)
  - All data which are older them 3 days and it is already reported is removed.
  - All folders which contains dumped data is compressed in a tar.gz file.

Data Structure
===============
  
The header of the CSVs are not included on the dumped file (it is probably a 
mistake), but it corresponds to (same as columns on the sqllite) which can be
easily described like bellow [11]:

  - user
      partition (text)
      pid (real)
      process (text)
      cpu_percent (real)
      cpu_time (real)
      cpu_num_threads (real)
      memory_percent (real)
      memory_rss (real)
      io_rw_counter (real)
      io_cycles_counter (real)
      date (text)
      time (text)
      reported (integer)

  - computer
      cpu_num_core (real)
      cpu_frequency (real
      cpu_type (text)
      memory_size (real)
      memory_type (text)
      partition_list (text)
      date (text)
      time (text)
      reported (integer)

  - system
      loadavg (real)
      cpu_percent (real)
      memory_used (real)
      memory_free (real)
      net_in_bytes (real)
      net_in_errors (real)
      net_in_dropped (real)
      net_out_bytes (real)
      net_out_errors (real)
      net_out_dropped (real)
      date (text)
      time (text)
      reported (integer)
    
  - disk
      partition (text)
      used (text)
      free (text)
      mountpoint (text)
      date (text)
      time (text)
      reported (integer) 

Probably a more formal way to collect data data can be introduced.

Download Collected Data
========================

Data is normally available on the server file system, we use a simple software 
"slapmonitor" which can be deployed on any machine which allow us download via 
HTTP the data. 

Slapmonitor can be also used to determinate de availability of the machine (it 
returns "OK" if accessed on his "/" address), and it servers the data on a url 
like:

  - https://<address>/ -> just return "OK"
  - https://<address>/<secret hash>/server-log/ -> you can see all files 

The slapmonitoring can be easily extented to include more sensors (like 
temperature, benchmarks...) which normally requires more speficic software 
configurations.

Planned Non core extensions and benchmarking
=============================================

 It is planned to include 4 simple benchmarks measure machines performance 
 degradation overtime:
 
   - CPU benchmark with Pystone
   - SQL Benchmark on SQLlite (for now)
   - Network Uplink Benchmark 
   - Network Download Benchmark
   
 This part is not included or coded, but we intent to measure performance 
 degradation in future, to stop to allocate if the machine is working but 
 cannot mantain a minimal Service Quality (even if it is not looks like 
 overloaded).
 
Servers Availability
=====================

All servers contacts the slapos master on regular bases (several times a minute), 
it is possible to determinate the general availability of a server by looking at
apache log using this script:

  - http://git.erp5.org/gitweb/cloud-quote.git/blob/HEAD:/py/my.py
  
It produces a json like this:

  - http://git.erp5.org/gitweb/cloud-quote.git/blob/HEAD:/data/stats.json
  
However, this is a bit draft and rudimentar to determinate problems on the 
machine, as the machine completly "death" is rare, normally most of failures are 
pure network problems or human/environmental problem (normally not depends of 
the machine load).


[1] http://git.erp5.org/gitweb/slapos.core.git/blob/HEAD:/slapos/collect/entity.py?js=1#l58
[2] http://git.erp5.org/gitweb/slapos.core.git/blob/HEAD:/slapos/collect/snapshot.py?js=1#l37
[3] http://git.erp5.org/gitweb/slapos.core.git/blob/HEAD:/slapos/collect/db.py?js=1#l130
[4] http://git.erp5.org/gitweb/slapos.core.git/blob/HEAD:/slapos/collect/entity.py?js=1#l77
[5] http://git.erp5.org/gitweb/slapos.core.git/blob/HEAD:/slapos/collect/snapshot.py?js=1#l62
[6] http://git.erp5.org/gitweb/slapos.core.git/blob/HEAD:/slapos/collect/snapshot.py?js=1#l95
[7] http://git.erp5.org/gitweb/slapos.core.git/blob/HEAD:/slapos/collect/snapshot.py?js=1#l81 
[8] http://git.erp5.org/gitweb/slapos.core.git/blob/HEAD:/slapos/collect/reporter.py?js=1#l75
[9] http://git.erp5.org/gitweb/slapos.core.git/blob/HEAD:/slapos/collect/reporter.py?js=1
[10] http://git.erp5.org/gitweb/slapos.core.git/blob/HEAD:/slapos/collect/db.py?js=1#l192
[11] http://git.erp5.org/gitweb/slapos.core.git/blob/HEAD:/slapos/collect/db.py?js=1#l39


                        



  
  
  
  
  
  