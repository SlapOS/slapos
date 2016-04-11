try:
  result_list = context.AcknowledgementTool_getUserUnreadAcknowledgementList()
except ValueError:
  result_list = []

if len(result_list):
  result_list = [result_list[0]]

import json
result = {
  "result": [{"text_content": "%s" % x['text_content'], "acknowledge_url": "%s" % x['acknowledge_url']} for x in result_list]
}

context.REQUEST.RESPONSE.setHeader('Content-Type', 'application/json')
return json.dumps(result)
