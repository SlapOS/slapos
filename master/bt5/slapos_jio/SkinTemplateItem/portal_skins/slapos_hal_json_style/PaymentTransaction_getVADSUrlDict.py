""" Return a dict with vads_urls required for payzen."""
if web_site is None:
  web_site = context.getWebSiteValue()

base_url = web_site.absolute_url()
payment_transaction_url = context.getRelativeUrl()

base = web_site.getLayoutProperty("configuration_payment_url_template",
                                 "%(url)s/#/%(payment)s?page=slap_payment_result&result=%(result)s")

base_substitution_dict = {
  "url" : base_url,
  "payment": payment_transaction_url,
  "result": "__RESULT__"
}

vads_url = base % base_substitution_dict

return dict(
  vads_url_already_registered=vads_url.replace("__RESULT__", "already_registered"),
  vads_url_cancel=vads_url.replace("__RESULT__", "cancel"),
  vads_url_error=vads_url.replace("__RESULT__", "error"),
  vads_url_referral=vads_url.replace("__RESULT__", "referral"),
  vads_url_refused=vads_url.replace("__RESULT__", "refused"),
  vads_url_success=vads_url.replace("__RESULT__", "success"),
  vads_url_return=vads_url.replace("__RESULT__", "return")
)
