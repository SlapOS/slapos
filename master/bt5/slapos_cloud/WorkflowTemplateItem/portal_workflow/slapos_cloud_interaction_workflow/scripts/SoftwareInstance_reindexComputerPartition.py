instance = state_change['object']
partition = instance.getAggregateValue(portal_type="Computer Partition")
if partition is not None:
  partition.activate(
    after_path_and_method_id=(instance.getPath(), ('immediateReindexObject', 'recursiveImmediateReindexObject'))).reindexObject()
