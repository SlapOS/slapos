import json
software_release = context.portal_catalog.getResultValue(
  url_string={'query': context.getUrlString(), 'key': 'ExactMatch'},
  portal_type='Software Release')

return json.dumps("%s (%s)" % (software_release.getTitle(), software_release.getVersion()))
