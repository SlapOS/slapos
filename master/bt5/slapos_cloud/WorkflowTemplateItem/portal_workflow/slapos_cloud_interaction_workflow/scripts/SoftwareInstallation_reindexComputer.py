installation = state_change['object']
computer = installation.getAggregateValue(portal_type="Computer")
if computer is not None:
  computer.activate(
    after_path_and_method_id=(installation.getPath(), ('immediateReindexObject', 'recursiveImmediateReindexObject'))).reindexObject()
