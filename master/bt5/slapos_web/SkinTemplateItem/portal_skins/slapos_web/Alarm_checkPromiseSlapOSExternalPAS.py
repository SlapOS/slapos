promise_dict = {
  'IExtractionPlugin': [
    'Vifib Browser ID Extraction Plugin',
    'Vifib Facebook Server Extraction Plugin',
    'Vifib Google Server Extraction Plugin',
#   'ERP5 Bearer Extraction Plugin',
    'ERP5 Facebook Extraction Plugin',
    'ERP5 Google Extraction Plugin',
  ],
}
context.Alarm_checkPromiseSlapOSPASBase(promise_dict, tag, fixit=fixit, **kw)
