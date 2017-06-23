portal = context.getPortalObject()
request = portal.REQUEST
reference = request['reference']
data_chunk = request['data_chunk']

module = portal.data_stream_module
try:
  data_stream = module[reference]
except KeyError:
  data_stream = module.newContent(reference, 'Data Stream')

append_method = context.getId()
if append_method == 'scalability_test_raw_lf':
  data_stream.appendData(data_chunk + '\n')
else:
  assert append_method == 'scalability_test_unpack', append_method
  for time, data_chunk in context.unpack(data_chunk):
    data_stream.appendData(data_chunk)
