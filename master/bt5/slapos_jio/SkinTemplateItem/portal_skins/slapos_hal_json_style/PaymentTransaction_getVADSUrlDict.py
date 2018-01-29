""" Return a dict with vads_urls required for payzen."""
web_site = context.getWebSiteValue()
base_url = web_site.absolute_url()
payment_transaction_url = context.getRelativeUrl()

return dict(
  vads_url_already_registered="%s/#/%s?page=slap_payment_result&n.result=already_registered" % (base_url, payment_transaction_url),
  vads_url_cancel="%s/#/%s?page=slap_payment_result&result=cancel" % (base_url, payment_transaction_url),
  vads_url_error="%s/#/%s?page=slap_payment_result&result=error" % (base_url, payment_transaction_url),
  vads_url_referral="%s/#/%s?page=slap_payment_result&result=referral" % (base_url, payment_transaction_url),
  vads_url_refused="%s/#/%s?page=slap_payment_result&result=refused" % (base_url, payment_transaction_url),
  vads_url_success="%s/#/%s?page=slap_payment_result&result=success" % (base_url, payment_transaction_url),
  vads_url_return="%s/#/%s?page=slap_payment_result&result=return" % (base_url, payment_transaction_url),
)
