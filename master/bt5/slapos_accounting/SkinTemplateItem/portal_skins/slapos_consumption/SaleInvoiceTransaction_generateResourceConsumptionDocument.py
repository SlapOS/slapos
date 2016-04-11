portal = context.getPortalObject()
invoice = context
document = portal.portal_catalog.getResultValue(
             portal_type="User Consumption HTML File",
             validation_state="shared",
             follow_up_uid=invoice.getUid()
           )

if document is None:
  document = portal.consumption_document_module.newContent(
        portal_type="User Consumption HTML File",
        title="Invoice Resource Comsuption %s" % invoice.getTitle(),
        reference="INVOICE-RC-%s" % invoice.getReference(),
        classification="personal/private",
        data=invoice.SaleInvoiceTransaction_getPrintoutResourceContent(),
        publication_section="other",
        contributor_value=invoice.getDestination(),
        follow_up=invoice.getRelativeUrl()
      )

  document.submit()
  document.share()

return document.getRelativeUrl()
