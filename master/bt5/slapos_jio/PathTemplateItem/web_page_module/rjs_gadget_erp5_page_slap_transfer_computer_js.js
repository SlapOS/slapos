/*global window, rJS, RSVP */
/*jslint nomen: true, indent: 2, maxerr: 3 */
(function (window, rJS, RSVP) {
  "use strict";

  rJS(window)
    /////////////////////////////////////////////////////////////////
    // Acquired methods
    /////////////////////////////////////////////////////////////////
    .declareAcquiredMethod("updateHeader", "updateHeader")
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("getUrlFor", "getUrlFor")
    .declareAcquiredMethod("redirect", "redirect")
    .declareAcquiredMethod("jio_putAttachment", "jio_putAttachment")
    .declareAcquiredMethod("jio_get", "jio_get")
    .declareAcquiredMethod("jio_allDocs", "jio_allDocs")
    .declareAcquiredMethod("notifySubmitting", "notifySubmitting")
    .declareAcquiredMethod("notifySubmitted", 'notifySubmitted')

    /////////////////////////////////////////////////////////////////
    // declared methods
    /////////////////////////////////////////////////////////////////
    .allowPublicAcquisition('notifySubmit', function () {
      return this.triggerSubmit();
    })

    .onEvent('submit', function () {
      var gadget = this;
      return gadget.notifySubmitting()
        .push(function () {
          return gadget.getDeclaredGadget('form_view');
        })
        .push(function (form_gadget) {
          return form_gadget.getContent();
        })
        .push(function (doc) {
          return gadget.getSetting("hateoas_url")
            .push(function (url) {
              // This is horrible
              return gadget.jio_putAttachment(doc.relative_url,
                url + doc.relative_url + "/Computer_createMovement", doc);
            })
            .push(function () {
              return gadget.notifySubmitted({message: 'Computer is transferred.', status: 'success'})
                .push(function () {
                // Workaround, find a way to open document without break gadget.
                return gadget.redirect({"command": "change",
                                      "options": {"jio_key": doc.relative_url, "page": "slap_controller"}});
              });
            });
        });
    })

    .declareMethod("triggerSubmit", function () {
      return this.element.querySelector('button[type="submit"]').click();
    })

    .declareMethod("render", function (options) {
      var gadget = this;
      return RSVP.Queue()
        .push(function () {
          return gadget.getSetting("me");
        })
        .push(function (setting) {
          return gadget.jio_get(setting);
        })
        .push(function (me) {
          var i, destination_list = '"NULL",', destination_project_list = '"NULL",';
          for (i in me.assignment_destination_project_list) {
            destination_project_list += '"' + me.assignment_destination_project_list[i] + '",';
          }
          for (i in me.assignment_destination_list) {
            destination_list += '"' + me.assignment_destination_list[i] + '",';
          }
          return RSVP.all([
              gadget.getDeclaredGadget('form_view'),
              gadget.jio_get(options.jio_key),
              gadget.jio_allDocs({
                query: 'portal_type:"Organisation" AND relative_url:(' + destination_list + ')',
                sort_on: [['reference', 'ascending']],
                select_list: ['reference', 'title']
              }),
              gadget.jio_allDocs({
                query: 'portal_type:"Project" AND validation_state:"validated" AND relative_url:(' + destination_project_list + ')',
                sort_on: [['reference', 'ascending']],
                select_list: ['reference', 'title']
              })
            ]);
        })
        .push(function (result) {
          var doc = result[1],
              site_list = [["", ""]],
              project_list = [["", ""]],
              i, value, project_len = result[3].data.total_rows,
              site_len = result[2].data.total_rows;

          for (i = 0; i < site_len; i += 1) {
            site_list.push([
              result[2].data.rows[i].value.title ? result[2].data.rows[i].value.title : result[2].data.rows[i].value.reference,
              result[2].data.rows[i].id
            ]);
          }

          for (i = 0; i < project_len; i += 1) {
            project_list.push([
              result[3].data.rows[i].value.title ? result[3].data.rows[i].value.title : result[3].data.rows[i].value.reference,
              result[3].data.rows[i].id
            ]);
          }

          return result[0].render({
            erp5_document: {
              "_embedded": {"_view": {
                "my_title": {
                  "description": "The name of a document in ERP5",
                  "title": "Title",
                  "default": doc.title,
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "key": "title",
                  "hidden": 0,
                  "type": "StringField"
                },
                "my_reference": {
                  "description": "The name of a document in ERP5",
                  "title": "Reference",
                  "default": doc.reference,
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "key": "reference",
                  "hidden": 0,
                  "type": "StringField"
                },
                "my_source": {
                  "description": "The name of a document in ERP5",
                  "title": "Current Location",
                  "default": doc.source_title,
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "key": "source_title",
                  "hidden": 0,
                  "type": "StringField"
                },
                "my_source_project": {
                  "description": "The name of a document in ERP5",
                  "title": "Current Project",
                  "default": doc.source_project_title,
                  "css_class": "",
                  "required": 1,
                  "editable": 0,
                  "key": "source_project_title",
                  "hidden": 0,
                  "type": "StringField"
                },
                "my_destination": {
                  "description": "The name of a document in ERP5",
                  "title": "Future Location",
                  "default": "",
                  "items": site_list,
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "destination",
                  "hidden": 0,
                  "type": "ListField"
                },
                "my_destination_project": {
                  "description": "The name of a document in ERP5",
                  "title": "Future Project",
                  "default": "",
                  "items": project_list,
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "destination_project",
                  "hidden": 0,
                  "type": "ListField"
                },
                "my_relative_url": {
                  "description": "",
                  "title": "Parent Relative Url",
                  "default": options.jio_key,
                  "css_class": "",
                  "required": 1,
                  "editable": 1,
                  "key": "relative_url",
                  "hidden": 1,
                  "type": "StringField"
                }
              }},
              "_links": {
                "type": {
                  // form_list display portal_type in header
                  name: ""
                }
              }
            },
            form_definition: {
              group_list: [[
                "left",
                [["my_title"], ["my_reference"], ["my_source"], ["my_source_project"], ["my_destination"], ["my_destination_project"], ["my_relative_url"]]
              ]]
            }
          });
        })
        .push(function () {
          return gadget.getSetting('document_title');
        })
        .push(function (document_title) {
          return gadget.updateHeader({
            page_title: "Transfer Computer",
            submit_action: true
          });
        });
    });
}(window, rJS, RSVP));