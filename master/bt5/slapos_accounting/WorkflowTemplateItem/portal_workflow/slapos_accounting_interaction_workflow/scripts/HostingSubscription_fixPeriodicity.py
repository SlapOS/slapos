from Products.ERP5Type.DateUtils import addToDate, getClosestDate
hosting_subscription = state_change['object']

edit_kw = {}

if hosting_subscription.getPeriodicityHour() is None:
  edit_kw['periodicity_hour_list'] = [0]
if hosting_subscription.getPeriodicityMinute() is None:
  edit_kw['periodicity_minute_list'] = [0]
if hosting_subscription.getPeriodicityMonthDay() is None:
  start_date = hosting_subscription.HostingSubscription_calculateSubscriptionStartDate()
  start_date = getClosestDate(target_date=start_date, precision='day')
  while start_date.day() >= 29:
    start_date = addToDate(start_date, to_add={'day': -1})
  edit_kw['periodicity_month_day_list'] = [start_date.day()]

if edit_kw:
  hosting_subscription.edit(**edit_kw)
