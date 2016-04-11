promise_dict = {
  'IExtractionPlugin': [
    'SlapOS Machine Authentication Plugin',
    'ERP5 Access Token Extraction Plugin',
  ],
  'IAuthenticationPlugin': [
    'SlapOS Machine Authentication Plugin',
    'SlapOS Shadow Authentication Plugin',
  ],
  'IGroupsPlugin': [
    'SlapOS Machine Authentication Plugin',
    'SlapOS Shadow Authentication Plugin',
  ],
  'IUserEnumerationPlugin': [
    'SlapOS Machine Authentication Plugin',
    'SlapOS Shadow Authentication Plugin',
  ]
}
context.Alarm_checkPromiseSlapOSPASBase(promise_dict, tag, fixit=fixit, **kw)
