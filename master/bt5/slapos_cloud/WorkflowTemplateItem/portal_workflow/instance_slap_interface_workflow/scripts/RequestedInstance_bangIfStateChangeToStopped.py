instance = state_change['object']
if (instance.getPortalType() in ["Software Instance", "Slave Instance"]) and (instance.getSlapState() != 'stop_requested'):
  instance.bang(bang_tree=False, comment="State changed from %s to stop_requested" % instance.getSlapState())
