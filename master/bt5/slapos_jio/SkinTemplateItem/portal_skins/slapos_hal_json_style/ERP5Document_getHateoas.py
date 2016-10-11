from zExceptions import Unauthorized
from AccessControl import getSecurityManager
from ZTUtils import make_query
from Products.ZSQLCatalog.SQLCatalog import Query, NegatedQuery
import json
if REQUEST is None:
  REQUEST = context.REQUEST
  # raise Unauthorized
if response is None:
  response = REQUEST.RESPONSE

url_template_dict = {
  "form_action": "%(traversed_document_url)s/%(action_id)s",
  "traverse_template": "%(root_url)s/%(script_id)s?mode=traverse" + \
                       "{&relative_url,view}",
  "search_template": "%(root_url)s/%(script_id)s?mode=search" + \
                     "{&query,select_list*,limit*}",
  "new_content_action": "%(root_url)s/%(script_id)s?mode=newContent",
  # XXX View is set by default to empty
  "document_hal": "%(root_url)s/%(script_id)s?mode=traverse" + \
                  "&relative_url=%(relative_url)s",
  "jio_get_template": "urn:jio:get:%(relative_url)s",
  "jio_search_template": "urn:jio:allDocs?%(query)s",
}

default_document_uri_template = url_template_dict["jio_get_template"]

def getFormRelativeUrl(form):
  return portal.portal_catalog(
    portal_type="ERP5 Form",
    uid=form.getUid(),
    id=form.getId(),
    limit=1,
    select_dict={'relative_url': None}
  )[0].relative_url

def renderField(field, meta_type=None):
  if meta_type is None:
    meta_type = field.meta_type

  if meta_type == "ProxyField":
    result = renderField(field, meta_type=field.getRecursiveTemplateField().meta_type)
  elif meta_type in ("ListField", "ParallelListField", "MultiListField"):
    result = {
      "type": meta_type,
      "key": field.generate_field_key(),
      "default": field.get_value("default"),
      "editable": field.get_value("editable"),
      "css_class": field.get_value("css_class"),
      "hidden": field.get_value("hidden"),
      "description": field.get_value("description"),
      "title": field.get_value("title"),
      "required": field.get_value("required"),
      # XXX Message can not be converted to json as is
      "items": field.get_value("items"),
    }
  elif meta_type in ("StringField", "FloatField", "RelationStringField",
                     "MultiRelationStringField", "EmailField", "TextAreaField",
                     "LinesField", "ImageField", "FileField", "IntegerField",
                     "PasswordField"):
    result = {
      "type": meta_type,
      "key": field.generate_field_key(),
      "default": field.get_value("default"),
      "editable": field.get_value("editable"),
      "css_class": field.get_value("css_class"),
      "hidden": field.get_value("hidden"),
      "description": field.get_value("description"),
      "title": field.get_value("title"),
      "required": field.get_value("required"),
    }
  elif meta_type == "ListBox":
    # XXX Not implemented
    columns = field.get_value("columns")

    # XXX 
#     list_method = getattr(traversed_document, traversed_document.Listbox_getListMethodName(field))
    # portal_types = [x[1] for x in field.get_value('portal_types')]
    portal_types = field.get_value('portal_types')
    default_params = dict(field.get_value('default_params'))
    # How to implement pagination?
    # default_params.update(REQUEST.form)
    lines = field.get_value('lines')
    list_method_name = traversed_document.Listbox_getListMethodName(field)
    list_method_query_dict = dict(
      portal_type=[x[1] for x in portal_types], **default_params
    )

    if (list_method_name == "portal_catalog"):
      pass
    elif (list_method_name in ("searchFolder", "objectValues")):
      list_method_query_dict["parent_uid"] = traversed_document.getUid()
    # XXX How to handle script queries?
#     else:
#       raise NotImplementedError("Unsupported list method %s" % list_method_name)
      


#     row_list = list_method(limit=lines, portal_type=portal_types,
#                            **default_params)
#     line_list = []
#     for row in row_list:
#       document = row.getObject()
#       line = {
#         "url": url_template_dict["document_hal"] % {
#           "root_url": site_root.absolute_url(),
#           "relative_url": document.getRelativeUrl(),
#           "script_id": script.id
#         }
#       }
#       for property, title in columns:
#         prop = document.getProperty(property)
#         if same_type(prop, DateTime()):
#           prop = "XXX Serialize DateTime"  
#         line[title] = prop
#         line["_relative_url"] = document.getRelativeUrl()
#       line_list.append(line)

    result = {
      "type": meta_type,
      # "column_list": [x[1] for x in columns],
      "column_list": columns,
#       "line_list": line_list,
      "title": field.get_value("title"),
      "key": field.generate_field_key(),
      "portal_type": portal_types,
      "lines": lines,
      "default_params": default_params,
      "list_method": list_method_name,
      "query": url_template_dict["jio_search_template"] % {
          "query": make_query({"query": sql_catalog.buildQuery(
            list_method_query_dict
          ).asSearchTextExpression(sql_catalog)})
        }
    }
  else:
    # XXX Not implemented
    result = {
      "type": meta_type,
      "_debug": "Unsupported field type",
      "title": field.get_value("title"),
      "key": field.generate_field_key(),
    }
  return result


def renderForm(form, response_dict):
  REQUEST.set('here', traversed_document)

  # Form action
  response_dict['_actions'] = {
    'put': {
      "href": url_template_dict["form_action"] % {
        "traversed_document_url": traversed_document.absolute_url(),
        "action_id": form.action
      },
      "method": form.method,
    }
  }
  # Form traversed_document
  response_dict['_links']['traversed_document'] = {
    "href": default_document_uri_template % {
      "root_url": site_root.absolute_url(),
      "relative_url": traversed_document.getRelativeUrl(),
      "script_id": script.id
    },
    "name": traversed_document.getRelativeUrl(),
    "title": traversed_document.getTitle()
  }

  response_dict['_links']['form_definition'] = {
#     "href": default_document_uri_template % {
#       "root_url": site_root.absolute_url(),
#       "script_id": script.id,
#       "relative_url": getFormRelativeUrl(form)
#     },
    "href": default_document_uri_template % {
      "relative_url": getFormRelativeUrl(form)
    },
    'name': form.id
  }

  group_list = []
  for group in form.Form_getGroupTitleAndId():

    if group['gid'].find('hidden') < 0:
#       field_list = []
      for field in form.get_fields_in_group(group['goid']):
#         field_list.append((field.id, renderRawField(field)))
        if field.get_value("enabled"):
          response_dict[field.id] = renderField(field)

  #       for field_group in field.form.get_groups():
  #         traversed_document.log("Field group: " + field_group)
  #         traversed_document.log(field_group)
  #         for field_property in field.form.get_fields_in_group(field_group):
  # #           traversed_document.log("Field attribute: " + field_property.id)
  # #           field.get_value(field_property.id)
  #           traversed_document.log(field_property)

#       group_list.append((group['gid'], field_list))

  response_dict["form_id"] = {
    "type": "StringField",
    "key": "form_id",
    "default": form.id,
    "editable": 0,
    "css_class": "",
    "hidden": 1,
    "description": "",
    "title": "form_id",
    "required": 1,
  }

#   response_dict["group_list"] = group_list
# rendered_response_dict["_embedded"] = {
#   "form": raw_response_dict
# }


# XXX form action update, etc
def renderRawField(field):
  meta_type = field.meta_type

  return {
    "meta_type": field.meta_type
  }


  if meta_type == "MethodField":
    result = {
      "meta_type": field.meta_type
    }
  else:
    result = {
      "meta_type": field.meta_type,
      "_values": field.values,
      # XXX TALES expression is not JSON serializable by default
      # "_tales": field.tales
      "_overrides": field.overrides
    }
  if meta_type == "ProxyField":
    result['_delegated_list'] = field.delegated_list
#     try:
#       result['_delegated_list'].pop('list_method')
#     except KeyError:
#       pass

  # XXX ListMethod is not JSON serialized by default
  try:
    result['_values'].pop('list_method')
  except KeyError:
    pass
  try:
    result['_overrides'].pop('list_method')
  except KeyError:
    pass
  return result


def renderFormDefinition(form, response_dict):
  group_list = []
  for group in form.Form_getGroupTitleAndId():

    if group['gid'].find('hidden') < 0:
      field_list = []

      for field in form.get_fields_in_group(group['goid']):
        field_list.append((field.id, renderRawField(field)))

      group_list.append((group['gid'], field_list))
  response_dict["group_list"] = group_list


context.Base_prepareCorsResponse(RESPONSE=response)

mime_type = 'application/hal+json'
portal = context.getPortalObject()
sql_catalog = portal.portal_catalog.getSQLCatalog()

# Calculate the site root to prevent unexpected browsing
is_web_mode = (context.REQUEST.get('current_web_section', None) is not None) or (hasattr(context, 'isWebMode') and context.isWebMode())
# is_web_mode =  traversed_document.isWebMode()
if is_web_mode:
  site_root = context.getWebSiteValue()
else:
  site_root = portal

# Check if traversed_document is the site_root
if relative_url:
  traversed_document = site_root.restrictedTraverse(relative_url)
else:
  traversed_document = context
is_site_root = (traversed_document.getPath() == site_root.getPath())
is_portal = (traversed_document.getPath() == portal.getPath())

result_dict = {
  '_debug': mode,
  '_links': {
    "self": {
      # XXX Include query parameters
      "href": traversed_document.Base_getRequestUrl()
    },
    # Always inform about site root
    "site_root": {
      "href": default_document_uri_template % {
        "root_url": site_root.absolute_url(),
        "relative_url": site_root.getRelativeUrl(),
        "script_id": script.id
      },
      "name": site_root.getTitle(),
    },
    # Always inform about portal
    "portal": {
      "href": default_document_uri_template % {
        "root_url": portal.absolute_url(),
        # XXX the portal has an empty getRelativeUrl. Make it still compatible
        # with restrictedTraverse
        "relative_url": portal.getId(),
        "script_id": script.id
      },
      "name": portal.getTitle(),
    }
  }
}


if mime_type != traversed_document.Base_handleAcceptHeader([mime_type]):
  response.setStatus(406)
  return ""


elif (mode == 'root') or (mode == 'traverse'):
  #################################################
  # Raw document
  #################################################
  if REQUEST.other['method'] != "GET":
    response.setStatus(405)
    return ""
  # Default properties shared by all ERP5 Document and Site
  action_dict = {}
#   result_dict['_relative_url'] = traversed_document.getRelativeUrl()

  # Add a link to the portal type if possible
  if not is_portal:
    result_dict['_links']['type'] = {
      "href": default_document_uri_template % {
        "root_url": site_root.absolute_url(),
        "relative_url": portal.portal_types[traversed_document.getPortalType()]\
                          .getRelativeUrl(), 
        "script_id": script.id
      },
      "name": traversed_document.getPortalType(),
    }

  # XXX Loop on form rendering
  erp5_action_dict = portal.Base_filterDuplicateActions(
    portal.portal_actions.listFilteredActionsFor(traversed_document))

  embedded_url = None
  embedded_action_key = None
  # XXX See ERP5Type.getDefaultViewFor
  for erp5_action_key in erp5_action_dict.keys():
    erp5_action_list = []
    for view_action in erp5_action_dict[erp5_action_key]:
      # Action condition is probably checked in Base_filterDuplicateActions
      erp5_action_list.append({
        'href': '%s' % view_action['url'],
        'name': view_action['id'],
        'title': view_action['title']
      })
      # Try to embed the form in the result
      if (view == view_action['id']):
        embedded_url = '%s' % view_action['url']
        embedded_action_key = "action_" + erp5_action_key

    if erp5_action_list:
      if len(erp5_action_list) == 1:
        erp5_action_list = erp5_action_list[0]
      # XXX Put a prefix to prevent conflict
      result_dict['_links']["action_" + erp5_action_key] = erp5_action_list

#   for view_action in erp5_action_dict.get('object_view', []):
#     traversed_document.log(view_action)
#     # XXX Check the action condition
# #     if (view is None) or (view != view_action['name']):
#     object_view_list.append({
#       'href': '%s' % view_action['url'],
#       'name': view_action['name']
#     })

#   # XXX Check that traversed_document is not the portal
#   if (traversed_document.getRelativeUrl() != portal.getRelativeUrl()) and (traversed_document.getRelativeUrl() != site_root.getRelativeUrl()):
#     parent = traversed_document.getParentValue()
#     if (is_web_mode and (parent.getRelativeUrl() != portal.getRelativeUrl())):
#       result_dict['_links']['parent'] = {
#         'href': '%s' % parent.absolute_url(),
#         'name': parent.getTitle()
#       }
# 
#   if (renderer_form is not None):
#     traversed_document_property_dict, renderer_form_json = traversed_document.Base_renderFormAsSomething(renderer_form)
#     result_dict['_embedded'] = {
#       'object_view': renderer_form_json
#     }
#     result_dict.update(traversed_document_property_dict)

  # XXX XXX XXX XXX
  if (embedded_url is not None):
    # XXX Try to fetch the form in the traversed_document of the document
    # Of course, this code will completely crash in many cases (page template
    # instead of form, unexpected action TALES expression). Happy debugging.
    # renderer_form_relative_url = view_action['url'][len(portal.absolute_url()):]
    form_id = embedded_url.split('?', 1)[0].split("/")[-1]
    # XXX Drop (or do something else...) all query parameters (?reset:int=1)
    # renderer_form = traversed_document.restrictedTraverse(form_id, None)
    # XXX Proxy field are not correctly handled in traversed_document of web site
    renderer_form = getattr(traversed_document, form_id)
#     traversed_document.log(form_id)
    if (renderer_form is not None):
      embedded_dict = {
        '_links': {
          'self': {
            'href': embedded_url
          }
        }
      }
      renderForm(renderer_form, embedded_dict)
      result_dict['_embedded'] = {
        '_view': embedded_dict
        # embedded_action_key: embedded_dict
      }
#       result_dict['_links']["_view"] = {"href": embedded_url}

      # Include properties in document JSON
      # XXX Extract from renderer form?
      for group in renderer_form.Form_getGroupTitleAndId():
        for field in renderer_form.get_fields_in_group(group['goid']):
          field_id = field.id
#           traversed_document.log(field_id)
          if field_id.startswith('my_'):
            property_name = field_id[len('my_'):]
#             traversed_document.log(property_name)
            property_value = traversed_document.getProperty(property_name, d=None)
            if (property_value is not None):
              if same_type(property_value, DateTime()):
                # Serialize DateTime
                property_value = rfc822()
              result_dict[property_name] = property_value 

  ##############
  # XXX Custom slapos code
  ##############
  if is_site_root:
    # Global action users for the jIO plugin
    # XXX Would be better to not hardcode them but put them as portal type
    # "actions" (search could be on portal_catalog document, traverse on all
    # documents, newContent on all, etc)
#     result_dict['_links']['object_search'] = {
#       'href': '%s/ERP5Site_viewSearchForm?portal_skin=Hal' % absolute_url,
#       'name': 'Global Search'
#     }
    result_dict['_links']['raw_search'] = {
      "href": url_template_dict["search_template"] % {
        "root_url": site_root.absolute_url(),
        "script_id": script.id
      },
      'name': 'Raw Search',
      'templated': True
    }
    result_dict['_links']['traverse'] = {
      "href": url_template_dict["traverse_template"] % {
        "root_url": site_root.absolute_url(),
        "script_id": script.id
      },
      'name': 'Traverse',
      'templated': True
    }
    action_dict['add'] = {
      "href": url_template_dict["new_content_action"] % {
        "root_url": site_root.absolute_url(),
        "script_id": script.id
      },
      'method': 'POST',
      'name': 'New Content',
    }

    # Handle also other kind of users: instance, computer, master
    person = portal.ERP5Site_getAuthenticatedMemberPersonValue()
    if person is not None:
      result_dict['_links']['me'] = {
        "href": default_document_uri_template % {
          "root_url": site_root.absolute_url(),
          "relative_url": person.getRelativeUrl(), 
          "script_id": script.id
        },
#         '_relative_url': person.getRelativeUrl()
      }

    query = sql_catalog.buildQuery({
        "portal_type": "Software Product",
        "validation_state": 'published'
      }).asSearchTextExpression(sql_catalog)
    http_query = make_query({
      "mode": "search",
      "query": query
    })
    result_dict['_links']['slapos_jump'] = {
      "href": "%s/%s?%s" % (site_root.absolute_url(), script.id, http_query),
      '_query': query,
      'name': 'public_software_product'
    }

  else:
    traversed_document_portal_type = traversed_document.getPortalType()
    if traversed_document_portal_type == "Person":
      query = sql_catalog.buildQuery({
          "portal_type": "Hosting Subscription",
          "default_destination_section_uid": traversed_document.getUid(),
          "validation_state": 'validated'
        }).asSearchTextExpression(sql_catalog)
      http_query = make_query({
        "mode": "search",
        "query": query
      })
      result_dict['_links']['slapos_jump'] = [{
        "href": "%s/%s?%s" % (site_root.absolute_url(), script.id, http_query),
        'name': 'current_hosting_subscription',
        '_query': query
      }]

      # List of validated computers
      query = sql_catalog.buildQuery({
          "portal_type": "Computer",
          "default_strict_allocation_scope_uid": "!=%s" % traversed_document.getPortalObject().portal_categories.allocation_scope.close.forever.getUid(),
          "validation_state": 'validated'
        }).asSearchTextExpression(sql_catalog)
      http_query = make_query({
        "mode": "search",
        "query": query
      })
      result_dict['_links']['slapos_jump'].append({
        "href": "%s/%s?%s" % (site_root.absolute_url(), script.id, http_query),
        'name': 'current_computer',
        '_query': query
      })

      # List of networks
      query = sql_catalog.buildQuery({
          "portal_type": "Computer Network",
        }).asSearchTextExpression(sql_catalog)
      http_query = make_query({
        "mode": "search",
        "query": query
      })
      result_dict['_links']['slapos_jump'].append({
        "href": "%s/%s?%s" % (site_root.absolute_url(), script.id, http_query),
        'name': 'current_network',
        '_query': query
      })

      # List of invoices
      query = sql_catalog.buildQuery({
          "portal_type": "Sale Invoice Transaction",
          "default_destination_section_uid": traversed_document.getUid(),
          "query": NegatedQuery(Query(title="Reversal Transaction for %")),
        }).asSearchTextExpression(sql_catalog)
      http_query = make_query({
        "mode": "search",
        "query": query
      })
      result_dict['_links']['slapos_jump'].append({
        "href": "%s/%s?%s" % (site_root.absolute_url(), script.id, http_query),
        'name': 'current_invoice',
        '_query': query
      })

      # List of tickets
      query = sql_catalog.buildQuery({
          "portal_type": ["Support Request", "Regularisation Request"],
          "default_destination_decision_uid": traversed_document.getUid(),
        }).asSearchTextExpression(sql_catalog)
      http_query = make_query({
        "mode": "search",
        "query": query
      })
      result_dict['_links']['slapos_jump'].append({
        "href": "%s/%s?%s" % (site_root.absolute_url(), script.id, http_query),
        'name': 'current_ticket',
        '_query': query
      })

      action_dict['request'] = {
        'href': "%s/Person_requestInstanceFromJio" % traversed_document.absolute_url(),
        'method': 'POST'
      }
      action_dict['request_computer'] = {
        'href': "%s/Person_requestComputerFromJio" % traversed_document.absolute_url(),
        'method': 'POST'
      }
      action_dict['request_computer_network'] = {
        'href': "%s/Person_requestComputerNetworkFromJio" % traversed_document.absolute_url(),
        'method': 'POST'
      }
      action_dict['request_ticket'] = {
        'href': "%s/Person_requestTicketFromJio" % traversed_document.absolute_url(),
        'method': 'POST'
      }

    elif traversed_document_portal_type == "Hosting Subscription":
      # Link to all ongoing Hosting Subscriptions
      query = sql_catalog.buildQuery({
          "portal_type": ["Software Instance", "Slave Instance"],
          "default_specialise_uid": traversed_document.getUid(),
          "validation_state": 'validated'
        }).asSearchTextExpression(sql_catalog)
      http_query = make_query({
        "mode": "search",
        "query": query
      })
      result_dict['_links']['slapos_jump'] = {
        "href": "%s/%s?%s" % (site_root.absolute_url(), script.id, http_query),
        'name': 'related_instance',
        '_query': query
      }

      # Actions to modify the hosting subscription
      action_dict['start'] = {
        'href': "%s/HostingSubscription_changeRequestedStateFromJio?action=started" % traversed_document.absolute_url(),
        'method': 'POST'
      }
      action_dict['stop'] = {
        'href': "%s/HostingSubscription_changeRequestedStateFromJio?action=stopped" % traversed_document.absolute_url(),
        'method': 'POST'
      }
      action_dict['destroy'] = {
        'href': "%s/HostingSubscription_changeRequestedStateFromJio?action=destroyed" % traversed_document.absolute_url(),
        'method': 'POST'
      }

    elif traversed_document_portal_type == "Software Installation":
      action_dict['destroy'] = {
        'href': "%s/SoftwareInstallation_destroyFromJio" % traversed_document.absolute_url(),
        'method': 'POST'
      }

    elif traversed_document_portal_type == "Software Product":
      # Link to all Software Releases
      query = sql_catalog.buildQuery({
          "portal_type": "Software Release",
          "default_aggregate_uid": traversed_document.getUid(),
          "validation_state": ["shared", "shared_alive", "released", "released_alive", "published", "published_alive"]
        }).asSearchTextExpression(sql_catalog)
      http_query = make_query({
        "mode": "search",
        "query": query
      })
      result_dict['_links']['slapos_jump'] = {
        "href": "%s/%s?%s" % (site_root.absolute_url(), script.id, http_query),
        'name': 'related_software_release',
        '_query': query
      }

    elif traversed_document_portal_type == "Computer":
      # Link to related Software Installation
      query = sql_catalog.buildQuery({
          "portal_type": "Software Installation",
          "default_aggregate_uid": traversed_document.getUid(),
          "validation_state": "validated"
        }).asSearchTextExpression(sql_catalog)
      http_query = make_query({
        "mode": "search",
        "query": query
      })
      result_dict['_links']['slapos_jump'] = {
        "href": "%s/%s?%s" % (site_root.absolute_url(), script.id, http_query),
        'name': 'related_software_installation',
        '_query': query
      }

      action_dict['update_allocation_scope'] = {
        'href': "%s/Computer_updateAllocationScopeFromJio" % traversed_document.absolute_url(),
        'method': 'POST'
      }
      action_dict['generate_certificate'] = {
        'href': "%s/Computer_requestNewComputerCertificateFromJio" % traversed_document.absolute_url(),
        'method': 'POST'
      }
      action_dict['revoke_certificate'] = {
        'href': "%s/Computer_revokeComputerCertificateFromJio" % traversed_document.absolute_url(),
        'method': 'POST'
      }
      action_dict['request_installation'] = {
        'href': "%s/Computer_requestInstallationFromJio" % traversed_document.absolute_url(),
        'method': 'POST'
      }

    elif traversed_document_portal_type == "Sale Invoice Transaction":
      result_dict['_links']['slapos_jump'] = {
        "href": "%s/SaleInvoiceTransaction_viewSlapOSPrintout" % traversed_document.absolute_url(),
        'name': 'current_printout',
      }

    elif traversed_document_portal_type in ["Support Request", "Regularisation Request"]:
      # Link to all Events
      query = sql_catalog.buildQuery({
          "default_follow_up_uid": traversed_document.getUid(),
        }).asSearchTextExpression(sql_catalog)
      http_query = make_query({
        "mode": "search",
        "query": query
      })
      result_dict['_links']['slapos_jump'] = {
        "href": "%s/%s?%s" % (site_root.absolute_url(), script.id, http_query),
        'name': 'related_event',
        '_query': query
      }

      action_dict['update'] = {
        'href': "%s/Ticket_updateFromJio" % traversed_document.absolute_url(),
        'method': 'POST'
      }

    elif traversed_document_portal_type == "ERP5 Form":
      renderFormDefinition(traversed_document, result_dict)

  # Define document action
  if action_dict:
    result_dict['_actions'] = action_dict


elif mode == 'search':
  #################################################
  # Portal catalog search
  #################################################
  if REQUEST.other['method'] != "GET":
    response.setStatus(405)
    return ""

  if query == "__root__":
    # XXX Hardcoded behaviour to get root object with jIO
    sql_list = [site_root]

  elif query == "__portal__":
    # XXX Hardcoded behaviour to get portal object with jIO
    sql_list = [portal]

#     document = site_root
#     document_result = {
# #       '_relative_url': site_root.getRelativeUrl(),
#       '_links': {
#         'self': {
#           "href": default_document_uri_template % {
#             "root_url": site_root.absolute_url(),
#             "relative_url": document.getRelativeUrl(), 
#             "script_id": script.id
#           },
#         },
#       }
#     }
#     for select in select_list:
#       document_result[select] = document.getProperty(select, d=None)
#     result_dict['_embedded'] = {"contents": [document_result]}
  else:
#     raise NotImplementedError("Unsupported query: %s" % query)
    

#   # XXX
#   length = len('/%s/' % portal.getId())
#   # context.log(portal.portal_catalog(full_text=query, limit=limit, src__=1))
#   context.log(query)
    if query:
      sql_list = portal.portal_catalog(full_text=query, limit=limit)
    else:
      sql_list = portal.portal_catalog(limit=limit)

  result_list = []

#   if (select_list is None):
#     # Only include links
#     for sql_document in sql_list:
#       document = sql_document.getObject()
#       result_list.append({
#         "href": default_document_uri_template % {
#           "root_url": site_root.absolute_url(),
#           "relative_url": document.getRelativeUrl(), 
#           "script_id": script.id
#         },
#       })
#     result_dict['_links']['contents'] = result_list
# 
#   else:

  # Cast to list if only one element is provided
  if same_type(select_list, ""):
    select_list = [select_list]

  for sql_document in sql_list:
    try:
      document = sql_document.getObject()
    except AttributeError:
      # XXX ERP5 Site is not an ERP5 document
      document = sql_document
    document_result = {
#       '_relative_url': sql_document.path[length:],
      '_links': {
        'self': {
          "href": default_document_uri_template % {
            "root_url": site_root.absolute_url(),
            # XXX ERP5 Site is not an ERP5 document
            "relative_url": document.getRelativeUrl() or document.getId(), 
            "script_id": script.id
          },
        },
      }
    }
    for select in select_list:
      property_value = document.getProperty(select, d=None)
      if property_value is not None:
        document_result[select] = property_value
    result_list.append(document_result)
  result_dict['_embedded'] = {"contents": result_list}

  result_dict['_query'] = query
  result_dict['_limit'] = limit
  result_dict['_select_list'] = select_list


elif mode == 'newContent':
  #################################################
  # Create new document
  #################################################
  if REQUEST.other['method'] != "POST":
    response.setStatus(405)
    return ""
  portal_type = REQUEST.form["portal_type"]
  module = portal.getDefaultModule(portal_type=portal_type)
  document = module.newContent(
    portal_type=portal_type
  )
  # http://en.wikipedia.org/wiki/Post/Redirect/Get
  response.setStatus(201)
  response.setHeader("X-Location",
    default_document_uri_template % {
      "root_url": site_root.absolute_url(),
      "relative_url": document.getRelativeUrl(),
      "script_id": script.id
    })
  return ''

elif mode == 'form':
  #################################################
  # Calculate form value
  #################################################
  if REQUEST.other['method'] != "GET":
    response.setStatus(405)
    return ""

  renderForm(form, result_dict)


# elif mode == 'form_definition':
#   #################################################
#   # Get raw form definitions
#   #################################################
#   if REQUEST.other['method'] != "GET":
#     response.setStatus(405)
#     return ""
# 
#   form = getattr(portal, skin_id)
#   renderFormDefinition(form, result_dict)

else:
  raise NotImplementedError, "Unsupported mode %s" % mode

response.setHeader('Content-Type', mime_type)
return json.dumps(result_dict, indent=2)
