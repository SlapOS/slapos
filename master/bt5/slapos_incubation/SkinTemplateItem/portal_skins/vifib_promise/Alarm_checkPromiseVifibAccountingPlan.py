from Products.CMFActivity.ActiveResult import ActiveResult

# XXX rafael: Hardcoded value is a convention on Vifib.
vifib = context.organisation_module['vifib_internet']

year = DateTime().year()
start_date = '%s/01/01' % year
stop_date = '%s/12/31' % (year + 1)

accounting_period = context.portal_catalog.getResultValue(
   portal_type='Accounting Period',
   parent_uid=vifib.getUid(),
   simulation_state='started',
   **{'delivery.start_date': start_date,
      'delivery.stop_date': stop_date
      }
    )

if accounting_period is None and fixit:
  accounting_period = vifib.newContent(portal_type='Accounting Period',
       start_date=start_date, stop_date=stop_date)
  accounting_period.start()

if accounting_period is None:
  summary = "Unable to find Accounting Plan for the current year."
  if fixit:
    summary += ", fixed."
    severity = 0
  else:
    severity = 1
  detail = "Period %s to %s" % (start_date, stop_date)
else:
  severity = 0
  summary = "Nothing to do."
  detail = ""

active_result = ActiveResult()
active_result.edit(
  summary=summary, 
  severity=severity,
  detail=detail)

context.newActiveProcess().postResult(active_result)
