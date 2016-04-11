instance = state_change["object"]

assert instance.getPortalType() == "Slave Instance"

instance.invalidate()
