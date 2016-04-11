default_document = context.getDefaultDocumentValue()

if default_document is not None:
  return default_document.asStrippedHTML()

return ""
