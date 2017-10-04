promise_dict = {
  'IExtractionPlugin': [
    'SlapOS Machine Authentication Plugin',
    'ERP5 Access Token Extraction Plugin',
  ],
  'IGroupsPlugin': [
    'SlapOS Shadow Authentication Plugin',
  ],
  'IUserEnumerationPlugin': [
    'SlapOS Shadow Authentication Plugin',
  ]
}
context.Alarm_checkPromiseSlapOSPASBase(promise_dict, tag, fixit=fixit, **kw)
