/*global window, rJS, jIO, FormData, XMLHttpRequestProgressEvent */
/*jslint indent: 2, maxerr: 3 */
(function (window, rJS, jIO) {
  "use strict";

  function createReplicatedJio(gadget, storage_dict, query) {

    var storage_url,
      the_storage,
      configuration,
      hashCode = function (s) {
        return s.split("").reduce(function(a,b){a=((a<<5)-a)+b.charCodeAt(0);return a&a},0);
      };

    the_storage = JSON.parse(JSON.stringify(storage_dict));
    while (the_storage.hasOwnProperty('sub_storage')) {
      the_storage = the_storage.sub_storage;
    }
    /*if (! the_storage.hawOwnProperty('url')) {
      throw new Error('Jio configuration must contain url!');
    } else {
      storage_url = the_storage.url;
    }*/
    storage_url = the_storage.url;

    configuration = {
      type: "replicate",
      query: query,
      use_remote_post: false,
      conflict_handling: 2,
      check_local_modification: false,
      check_local_creation: false,
      check_local_deletion: false,
      check_remote_modification: true,
      check_remote_creation: true,
      check_remote_deletion: true,
      local_sub_storage: {
        type: "uuid",
        sub_storage: {
          type: "query",
          sub_storage: {
            type: "indexeddb",
            database: "monitoringdb_" + hashCode(storage_url)
          }
        }
      },
      remote_sub_storage: storage_dict
    };

    return jIO.createJIO(configuration);
  }

  function createOPMLReplicatedJio(url) {
    var jio_options = {
        type: "replicate",
        query: {},
        use_remote_post: false,
        conflict_handling: 2,
        check_local_modification: false,
        check_local_creation: false,
        check_local_deletion: false,
        check_remote_modification: true,
        check_remote_creation: true,
        check_remote_deletion: true,
        local_sub_storage: {
          type: "uuid",
          sub_storage: {
            type: "query",
            sub_storage: {
              type: "indexeddb",
              database: "monitoringdb"
            }
          }
        },
        remote_sub_storage: {
          type: "query",
          sub_storage: {
            type: "feed",
            feed_type: 'opml',
            url: url
          }
        }
      },
      jio_storage = jIO.createJIO(jio_options);

    return jio_storage;
  }

  function syncMonitoringOpmlData(url) {
    var jio_storage = createOPMLReplicatedJio(url);
    console.log("Sync of " + url);
    return jio_storage.repair()
      .push(function () {
        return {error: false, url: url};
      }, function(error) {
        console.log(error);
        return {error: true, url: url};
      });
  }

  function getFeedUrlList(query) {
    var jio_options = {
        type: "query",
        sub_storage: {
          type: "uuid",
          sub_storage: {
            type: "indexeddb",
            database: "monitoringdb"
          }
        }
      },
      jio_storage = jIO.createJIO(jio_options);
    if (query === undefined) {
      query = {
        include_docs: true
      };
    }
    return jio_storage.allDocs(query)
      .push(function (url_list) {
        var i,
        feed_url_list = [];
        for (i = 0; i < url_list.data.total_rows; i += 1) {

          if (url_list.data.rows[i].doc.htmlurl) { // || url_list.data.rows[i].doc.xmlUrl
            feed_url_list.push(url_list.data.rows[i].doc.htmlurl); // || url_list.data.rows[i].doc.xmlUrl
          }
        }
        return feed_url_list;
      }, function(error) {
        console.log(error);
      });
  }

  function getMonitorUrlList(query, opml_title) {
    var jio_options = {
        type: "query",
        sub_storage: {
          type: "uuid",
          sub_storage: {
            type: "indexeddb",
            database: "monitoringdb"
          }
        }
      },
      jio_storage = jIO.createJIO(jio_options);
    if (query === undefined) {
      query = {
        include_docs: true
      };
    }
    return jio_storage.allDocs(query)
      .push(function (url_list) {
        var i,
        monitor_url_list = [];
        for (i = 0; i < url_list.data.total_rows; i += 1) {
          if (url_list.data.rows[i].doc.url) {
            if ((opml_title && url_list.data.rows[i].doc.opml_title === opml_title)
                || (opml_title === undefined)) {
              monitor_url_list.push(url_list.data.rows[i].doc.url);
            }
          }
        }
        return monitor_url_list;
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

    .declareMethod('createJio', function (jio_options, replicated, query) {
      var gadget = this,
        storage;
      if ((replicated === undefined || replicated === true) && jio_options) {
        if (query === undefined) {
          query = {};
        }
        this.state_parameter_dict.jio_storage = createReplicatedJio(
          gadget, jio_options, query);
      } else {
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
      }

      return this.state_parameter_dict.jio_storage;
    })
    .declareMethod('syncMonitoringOpmlData', function (url) {

      if (url !== undefined) {
        return syncMonitoringOpmlData(url);
      }
      return this.getSetting('monitor_url_description')
        .push(function (url_description_dict) {
          var promise_list = [],
            key;
          for (key in url_description_dict) {
            promise_list.push(syncMonitoringOpmlData(url_description_dict[key].href));
          }
          return RSVP.all(promise_list);
        });
    })
    .declareMethod('getFeedUrlList', function (query) {
      return getFeedUrlList(query);
    })
    .declareMethod('getUrlFeedDescription', function (query) {
      var jio_options = {
          type: "query",
          sub_storage: {
            type: "uuid",
            sub_storage: {
              type: "indexeddb",
              database: "monitoringdb"
            }
          }
        },
        jio_storage = jIO.createJIO(jio_options);
      if (query === undefined) {
        query = {
          include_docs: true
        };
      }
      return jio_storage.allDocs(query)
        .push(function (url_list) {
          var i,
          feed_url_list = [];
          for (i = 0; i < url_list.data.total_rows; i += 1) {
            if (url_list.data.rows[i].doc.htmlurl || url_list.data.rows[i].doc.xmlurl) {
              feed_url_list.push({
                htmlurl: url_list.data.rows[i].doc.htmlurl,
                xmlUrl: url_list.data.rows[i].doc.xmlurl,
                url: url_list.data.rows[i].doc.url,
                title: url_list.data.rows[i].doc.title,
                opml_title: url_list.data.rows[i].doc.opml_title,
                type: url_list.data.rows[i].doc.type,
                create_date: url_list.data.rows[i].doc.create_date,
                modified_date: url_list.data.rows[i].doc.modified_date,
                version: url_list.data.rows[i].doc.version,
                text: url_list.data.rows[i].doc.text,
              });
            }
          }
          return feed_url_list;
        });
    })
    .declareMethod('getMonitorUrlList', function (query, opml_title) {
      return getMonitorUrlList(query, opml_title);
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
          throw error;
        });
    });

}(window, rJS, jIO));
