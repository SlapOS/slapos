
def get_user_list(config):
  nb_user = int(config.get("slapformat", "partition_amount"))
  name_prefix = config.get("slapformat", "user_base_name")
  path_prefix = config.get("slapformat", "partition_base_name")
  instance_root = config.get("slapos", "instance_root")
  user_dict = {name: User(name, path)
      for name, path in [
          (
            "%s%s" % (name_prefix, nb),
            "%s/%s%s" % (instance_root, path_prefix, nb)
          ) for nb in range(nb_user)
        ]
      }

  #user_dict['root'] = User("root", "/opt/slapgrid")
  return user_dict

class User(object):
  def __init__(self, name, path):
    self.name = str(name)
    self.path = str(path)
    self.snapshot_list = []

  def append(self, value):
    self.snapshot_list.append(value)

  def save(self, database, collected_date, collected_time):
    """ Insert collected data on user collector """
    database.connect()
    for snapshot_item in self.snapshot_list:
      database.insertUserSnapshot(self.name,
            pid=snapshot_item.get("pid"),
            process=snapshot_item.get("process"),
            cpu_percent=snapshot_item.get("cpu_percent"),
            cpu_time=snapshot_item.get("cpu_time"),
            cpu_num_threads=snapshot_item.get("cpu_num_threads"),
            memory_percent=snapshot_item.get("memory_percent"),
            memory_rss=snapshot_item.get("memory_rss"),
            io_rw_counter=snapshot_item.get("io_rw_counter"),
            io_cycles_counter=snapshot_item.get("io_cycles_counter"),
            insertion_date=collected_date, 
            insertion_time=collected_time)
    database.commit()
    database.close()

class Computer(dict):

  def __init__(self, computer_snapshot):
    self.computer_snapshot = computer_snapshot

  def save(self, database, collected_date, collected_time):
    database.connect()
    self._save_computer_snapshot(database, collected_date, collected_time)
    self._save_system_snapshot(database, collected_date, collected_time)
    self._save_disk_partition_snapshot(database, collected_date, collected_time)
    database.commit()
    database.close()

  def _save_computer_snapshot(self, database, collected_date, collected_time):
    partition_list = ";".join(["%s=%s" % (x,y) for x,y in \
                                  self.computer_snapshot.get("partition_list")])
    database.insertComputerSnapshot(
            cpu_num_core=self.computer_snapshot.get("cpu_num_core"), 
            cpu_frequency=self.computer_snapshot.get("cpu_frequency"),
            cpu_type=self.computer_snapshot.get("cpu_type"),
            memory_size=self.computer_snapshot.get("memory_size"),
            memory_type=self.computer_snapshot.get("memory_type"), 
            partition_list=partition_list,
            insertion_date=collected_date, 
            insertion_time=collected_time)

  def _save_system_snapshot(self, database, collected_date, collected_time):
    snapshot = self.computer_snapshot.get("system_snapshot")
    database.insertSystemSnapshot(
      loadavg=snapshot.get("load"),
      cpu_percent=snapshot.get("cpu_percent"), 
      memory_used=snapshot.get("memory_used"), 
      memory_free=snapshot.get("memory_free"),
      net_in_bytes=snapshot.get("net_in_bytes"),
      net_in_errors=snapshot.get("net_in_errors"),
      net_in_dropped=snapshot.get("net_in_dropped"),
      net_out_bytes=snapshot.get("net_out_bytes"),
      net_out_errors= snapshot.get("net_out_errors"),
      net_out_dropped=snapshot.get("net_out_dropped"),
      insertion_date=collected_date, 
      insertion_time=collected_time)

  def _save_disk_partition_snapshot(self, database, collected_date, collected_time):
    for disk_partition in self.computer_snapshot.get("disk_snapshot_list"):
      database.insertDiskPartitionSnapshot(
         partition=disk_partition.partition,
         used=disk_partition.disk_size_used,
         free=disk_partition.disk_size_free,
         mountpoint=';'.join(disk_partition.mountpoint_list),
         insertion_date=collected_date, 
         insertion_time=collected_time)

