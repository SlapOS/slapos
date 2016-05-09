if context.getPortalType() not in [ "System Preference"]:
  return []

if context.getPreferenceState() != "global":
  return []


portal = context.getPortalObject()
system_preference = context
promise_url = portal.getPromiseParameter('external_service', 'cloudooo_url')

if promise_url is None:
  return

url = "cloudooo://%s:%s/" % (system_preference.getPreferredOoodocServerAddress(), system_preference.getPreferredOoodocServerPortNumber())

if promise_url != url:
  fixing = ''
  if fixit:
    domain_port = promise_url.split('//')[1].split('/')[0]
    port = domain_port.split(':')[-1]
    domain = domain_port[:-(len(port)+1)]
    
    system_preference.edit(
      preferred_ooodoc_server_address=domain,
      preferred_ooodoc_server_port_number=port,
    )
    fixing = ' (fixed)'
  return ["Conversion Server not configured as expected%s: %s" %
    (fixing, "Expect %s\nGot %s" % (promise_url, url))]
else:
  return []
