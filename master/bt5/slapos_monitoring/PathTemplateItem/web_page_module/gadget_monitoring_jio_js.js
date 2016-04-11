/*global window, rJS, jIO, FormData, XMLHttpRequestProgressEvent */
/*jslint indent: 2, maxerr: 3 */
(function (window, rJS, jIO) {
  "use strict";

  function getOPMLUrlList(url, query) {
    var jio_options = {
        type: "query",
        sub_storage: {
          type: "feed",
          feed_type: 'opml',
          url: url
        }
      },
      jio_storage = jIO.createJIO(jio_options);
    if (query === undefined) {
      query = {};
    }
    return jio_storage.allDocs(query)
      .push(function (url_list) {
        var i,
        feed_url = [];
        for (i = 0; i < url_list.data.total_rows; i += 1) {
          if (url_list.data.rows[i].value.htmlurl) { // || url_list.data.rows[i].value.xmlUrl
            feed_url.push(url_list.data.rows[i].value.htmlurl); // || url_list.data.rows[i].value.xmlUrl
          }
        }
        return feed_url;
      }, function(error) {
        console.log(error);
      });
  }

  function getMonitorUrlList(url, query) {
    var jio_options = {
        type: "query",
        sub_storage: {
          type: "feed",
          feed_type: 'opml',
          url: url
        }
      },
      jio_storage = jIO.createJIO(jio_options);
    if (query === undefined) {
      query = {};
    }
    return jio_storage.allDocs(query)
      .push(function (url_list) {
        var i,
        monitor_url = [];
        for (i = 0; i < url_list.data.total_rows; i += 1) {
          if (url_list.data.rows[i].value.url) {
            monitor_url.push(url_list.data.rows[i].value.url);
          }
        }
        return monitor_url;
      }, function(error) {
        console.log(error);
      });
  }

  function concatArrayOfArray(arrayList) {
    var all_list = [],
      i;
    for (i = 0; i < arrayList.length; i += 1) {
      all_list = all_list.concat(arrayList[i]);
    }
    return all_list;
  }

  rJS(window)

    .ready(function (gadget) {
      // Initialize the gadget local parameters
      gadget.state_parameter_dict = {};
    })

    .declareAcquiredMethod("redirect", "redirect")
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("setSetting", "setSetting")

    .declareMethod('createJio', function (jio_options) {
      var gadget = this;
      if (jio_options === undefined) {
        jio_options = {
          type: "query",
          sub_storage: {
            type: "uuid",
            sub_storage: {
              type: "indexeddb",
              database: "monitoringdb"
            }
          }
        };
      }
      this.state_parameter_dict.jio_storage = jIO.createJIO(jio_options);
      return this.getSetting("jio_storage_name")
        .push(function (jio_storage_name) {
          gadget.state_parameter_dict.jio_storage_name = jio_storage_name;
        });
    })
    .declareMethod('createJioFromRssFeed', function (feed_url, basic_login) {
      var gadget = this,
        jio_options = {
          type: "query",
          sub_storage: {
            type: "feed",
            feed_type: 'rss',
            url: opml_url
          }
        };
      if (basic_login !== undefined) {
        jio_options.sub_storage.basic_login = basic_login;
      }
      this.state_parameter_dict.jio_storage = jIO.createJIO(jio_options);
      return jio_options;
    })
    .declareMethod('getUrlListFromOPML', function (opml_url, query) {
      return getOPMLUrlList(opml_url, query);
    })
    .declareMethod('getUrlDescriptionFromOPML', function (opml_url, query) {
      var jio_options = {
          type: "query",
          sub_storage: {
            type: "feed",
            feed_type: 'opml',
            url: opml_url
          }
        },
        jio_storage = jIO.createJIO(jio_options);
      if (query === undefined) {
        query = {};
      }
      return jio_storage.allDocs(query)
        .push(function (url_list) {
          var i,
          feed_url;
          for (i = 0; i < url_list.data.total_rows; i += 1) {
            if (url_list.data.rows[i].value.htmlurl || url_list.data.rows[i].value.xmlUrl) {
              feed_url.push({
                htmlurl: url_list.data.rows[i].value.htmlurl,
                xmlUrl: url_list.data.rows[i].value.xmlUrl,
                title: url_list.data.rows[i].value.title,
                opml_title: url_list.data.rows[i].value.opml_title,
                type: url_list.data.rows[i].value.type,
                create_date: url_list.data.rows[i].value.create_date,
                modified_date: url_list.data.rows[i].value.modified_date,
                version: url_list.data.rows[i].value.version,
                text: url_list.data.rows[i].value.text,
              });
            }
          }
          return feed_url;
        });
    })
    .declareMethod('getUrlListFromFullOPML', function (query) {
      return this.getSetting('monitor_url_description')
        .push(function (url_description_dict) {
          var promise_list = [],
            key;
          for (key in url_description_dict) {
            promise_list.push(getOPMLUrlList(url_description_dict[key].href, query));
          }
          return RSVP.all(promise_list);
        })
        .push(function(url_list) {
          return concatArrayOfArray(url_list);
        });
    })
    .declareMethod('getMonitorUrlList', function (query) {
      return this.getSetting('monitor_url_description')
        .push(function (url_description_dict) {
          var promise_list = [],
            key;
          for (key in url_description_dict) {
            promise_list.push(getMonitorUrlList(url_description_dict[key].href, query));
          }
          return RSVP.all(promise_list);
        })
        .push(function(url_list) {
          return concatArrayOfArray(url_list);
        });
    })
    .declareMethod('getMonitorUrlListFromOpml', function (url, query) {
      return getMonitorUrlList(url, query);
    })
    .declareMethod('allDocs', function () {
      var storage = this.state_parameter_dict.jio_storage;
      return storage.allDocs.apply(storage, arguments)
        .push(function (doc) {
          return doc;
        }, function (error) {
          console.log(error);
          // XXX - We must do something here (try to get document from local ? or raise)
          return undefined;
        });
    })
    .declareMethod('allAttachments', function () {
      var storage = this.state_parameter_dict.jio_storage;
      return storage.allAttachments.apply(storage, arguments);
    })
    .declareMethod('get', function () {
      var storage = this.state_parameter_dict.jio_storage;
      return storage.get.apply(storage, arguments);
    })
    .declareMethod('put', function () {
      var storage = this.state_parameter_dict.jio_storage;
      return storage.put.apply(storage, arguments);
    })
    .declareMethod('post', function () {
      var storage = this.state_parameter_dict.jio_storage;
      return storage.post.apply(storage, arguments);
    })
    .declareMethod('remove', function () {
      var storage = this.state_parameter_dict.jio_storage;
      return storage.remove.apply(storage, arguments);
    })
    .declareMethod('getAttachment', function () {
      var storage = this.state_parameter_dict.jio_storage;
      return storage.getAttachment.apply(storage, arguments);
    })
    .declareMethod('putAttachment', function () {
      var storage = this.state_parameter_dict.jio_storage;
      return storage.putAttachment.apply(storage, arguments);
    })
    .declareMethod('removeAttachment', function () {
      var storage = this.state_parameter_dict.jio_storage;
      return storage.removeAttachment.apply(storage, arguments);
    })
    .declareMethod('repair', function () {
      var gadget = this,
        storage = gadget.state_parameter_dict.jio_storage;
      return storage.repair.apply(storage, arguments)
        .push(undefined, function (error) {
          if (error instanceof XMLHttpRequestProgressEvent &&
              error.currentTarget.status === 401 &&
              gadget.state_parameter_dict.jio_storage_name === "ERP5") {
            return {
              redirect: {
                page: "login"
              }
            };
          }
          throw error;
        });
    });

}(window, rJS, jIO));