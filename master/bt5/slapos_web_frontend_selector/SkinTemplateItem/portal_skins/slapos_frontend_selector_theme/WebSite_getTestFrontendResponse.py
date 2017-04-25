if REQUEST is None:
  REQUEST = context.REQUEST
if response is None:
  response = REQUEST.RESPONSE


# Do not allow to put inside an iframe
response.setHeader("X-Frame-Options", "SAMEORIGIN")
response.setHeader("X-Content-Type-Options", "nosniff")

# Only fetch code (html, js, css, image) and data from this ERP5, to prevent any data leak as the web site do not control the gadget's code
response.setHeader('Content-Type', 'text/plain')

response.setHeader("Content-Security-Policy", "default-src 'none'; img-src 'self' data:; media-src 'self'; connect-src 'self' mail.tiolive.com *.erp5.cn; script-src 'self' 'unsafe-eval'; font-src netdna.bootstrapcdn.com; style-src 'self' netdna.bootstrapcdn.com 'unsafe-inline' data:; frame-src 'self' data:")

response.setHeader("Access-Control-Allow-Origin", "http://demoapp.node.grandenet.cn")

return """
###################################################################################
###################################################################################
###################################################################################
###################################################################################
###################################################################################
###################################################################################
###################################################################################
###################################################################################
###################################################################################
###################################################################################
###################################################################################
###################################################################################
"""
