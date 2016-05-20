from zExceptions import Unauthorized

if REQUEST is not None:
  raise Unauthorized


computer_partition = context.getAggregateValue()

if computer_partition is None:
  return ""

for ip in computer_partition.objectValues(
    portal_type="Internet Protocol Address"):

  ip_address = ip.getIpAddress("")
  if ":" in ip_address:
    return ip_address

return ""
