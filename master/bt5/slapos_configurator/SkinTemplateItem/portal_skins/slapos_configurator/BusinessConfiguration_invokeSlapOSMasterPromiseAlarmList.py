"""
  Solve all alarms which starts with id as "promise_vifib*".

  (rafael): This approach could be generalized on 
      configurator level, by providing a list of 
      alarms to be invoked always.
"""
alarm_to_solve_list = ['promise_certificate_autority_tool',
                       'promise_conversion_server',
                       'promise_kumofs_server',
                       'promise_mailhost_configuration',
                       'promise_memcached_server']

for alarm in context.portal_alarms.contentValues():
  alarm_id = alarm.getId()
  if alarm_id.startswith("promise_slapos") or \
                   alarm_id in alarm_to_solve_list:
    context.log("Solve %s" % alarm_id)
    alarm.solve()
