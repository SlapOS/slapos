from zExceptions import Unauthorized
from DateTime import DateTime
import json
if REQUEST is not None:
  raise Unauthorized

portal = context.getPortalObject()

person = portal.portal_membership.getAuthenticatedMember().getUserValue()

if person is None:
  # Create a Person document in order to generate the invoice.
  person = portal.person_module.newContent(
    portal_type="Person",
    default_email_text=email,
    first_name=user_input_dict["name"])

  login = person.newContent(portal_type="ERP5 Login",
                    reference=email,
                    # Please generate a LAAARGE random password.
                    password=email)

  login.validate()
  person.validate()
  person.immediateReindexObject()
  login.immediateReindexObject()

# Get Subscription condition for this Subscription Request
subscription_configuration = {
    "instance_xml": "", #context.getTextContent(),
    "title": "%s" % "Subscription for %s %s" % ("vm", email), #(context.getTitle(), email),
    "software_type": "cluster",#context.getSourceReference(),
    "url": "http://ww.com/sss",#context.getUrlString(),
    "shared": 0, #context.getRootSlave(),
    "subject_list": [], #context.getSubjectList(),
    "sla_xml": "", #context.getSlaXml()
}

software_title = subscription_configuration["title"]

subscription_request = portal.portal_catalog.getResultValue(
              portal_type='Subscription Request',
              title=software_title,
              validation_state=('draft', 'submitted',)
)

# How to consider that an Subscription request is already there.
# Perhaps if a user return, he should be able to resume a subscription process.
if subscription_request is not None:
  return json.dumps("already-requested")

now = DateTime()

subscription_request = context.subscription_request_module.newContent(
  source_reference=subscription_configuration["software_type"],
  title=software_title,
  url_string=subscription_configuration["url"],
  text_content=subscription_configuration["instance_xml"],
  start_date=now,
  stop_date=now + 30,
  root_slave=subscription_configuration["shared"],
  subject_list=subscription_configuration["subject_list"],
  destination_section_value=person
)

subscription_request.setDefaultEmailText(email)

def wrapWithShadow(subscription_request, amount):
  return subscription_request.SubscriptionRequest_requestPaymentTransaction(amount=amount,
                                                          tag="subscription_%s" % subscription_request.getId())

payment = person.Person_restrictMethodAsShadowUser(
  shadow_document=person,
  callable_object=wrapWithShadow,
  argument_list=[subscription_request, user_input_dict["amount"]])

if batch_mode:
  return {'subscription' : subscription_request.getRelativeUrl(), 'payment': payment.getRelativeUrl() }


return payment.PaymentTransaction_redirectToSubscriptionManualPayzenPayment(context.getWebSiteValue())
