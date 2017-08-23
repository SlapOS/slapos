/*jslint nomen: true, maxlen:200, indent:2*/
/*global window, document, rJS, console, RSVP, L, $, Image */
(function (window, document, rJS, RSVP) {
  "use strict";

  rJS(window)
    .ready(function (g) {
      g.props = {};
    })
    .ready(function (g) {
      g.props.deferred = new RSVP.defer();
    })
    .ready(function (g) {
      return g.getElement()
        .push(function (element) {
          g.props.element = element;
        });
    })
    .declareAcquiredMethod("notifyChange", "notifyChange")
    .declareAcquiredMethod("getUrlFor", "getUrlFor")
    .declareAcquiredMethod("getSetting", "getSetting")


    .declareMethod('render', function (options) {
      var gadget = this,
        map_gadget_list =  gadget.element.querySelectorAll(".custom-map-wrap"),
        queue = new RSVP.Queue();
      gadget.options = options;

      if (!gadget.options.doc) {
        gadget.options.doc = {};
      }

      if (map_gadget_list.length >= 2) {
        map_gadget_list[0].remove();
      }
      function readImageRatio(src) {
        var img = new Image();
        return new RSVP.Promise(function (resolve, reject, notify) {
          img.addEventListener("load", function () {
            resolve(img.width / img.height);
          });
          img.addEventListener("error", reject);
          img.addEventListener("progress", notify);
          img.src = src;
        });
      }

      if (options.image) {
        queue.push(function () {
          return readImageRatio(options.image);
        });
      }
      queue
        .push(function (result) {
          gadget.options.ratio = result;
          return gadget.props.deferred.resolve();
        });
    })
    .declareMethod('getContent', function (options) {
      var gadget = this,
        result = [],
        tmp,
        i;
      for (i = 0; i < gadget.props.new_marker_list.length; i += 1) {
        tmp = gadget.props.new_marker_list[i].getLatLng();
        result.push({latitude: tmp.lat, longitude: tmp.lng});
      }
      return result;
    })
    .declareService(function () {
      var gadget = this,
        map_element,
        latitude,
        longitude,
        zoom,
        marker_list,
        new_marker_list = [],
        marker_link,
        marker_label,
        marker_space,
        marker_monitor_link,
        group,
        redIcon,
        map,
        osmUrl = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        osm,
        osmAttribution = 'Map data &copy;' +
                         '<a href="https://openstreetmap.org">OpenStreetMap</a> contributors, ' +
                         '<a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, ' +
                         'Imagery © <a href="http://mapbox.com">Mapbox</a>',
        marker,
        marker_options = {},
        queue,
        m,
        i,
        bounds,
        list,
        yx = L.latLng;

      function xy(x, y) {
        if (L.Util.isArray(x)) {// When doing xy([x, y])
          return yx(x[1], x[0]);
        }
        return yx(y, x);  // When doing xy(x, y);
      }
      return new RSVP.Queue()
        .push(function () {
          return gadget.props.deferred.promise;
        })
        .push(function () {
          var l = [],
              marker_list = gadget.options.marker_list || [];
          for (i = 0; i < marker_list.length; i += 1) {
            l.push(gadget.getUrlFor({command: "change",
                                   options: {jio_key: marker_list[i].jio_key,
                                             page: "slap_controller"}}));
          }
          l.push(gadget.getSetting("hateoas_url"));
          return RSVP.all(l);
        })
        .push(function (url_list) {
          var hateoas_url = url_list.pop();
          map_element = gadget.props.element.querySelector(".map"),
          latitude = gadget.options.doc.latitude || 0,
          longitude = gadget.options.doc.longitude || 0,
          zoom = gadget.options.zoom || 0,
          marker_list = gadget.options.marker_list || [];
          redIcon = L.icon({iconUrl: "hateoas/marker-icon-mod-100-70-10.png",
                           shadowUrl: "hateoas/marker-shadow.png",
                           iconSize: [25, 41],
                           iconAnchor: [12, 41],
                           popupAnchor: [1, -34],
                           shadowSize: [41, 41]});

          if (gadget.options.view_mode === undefined || gadget.options.view_mode === 'map') {
            osm = new L.TileLayer(osmUrl, {maxZoom: 18, attribution: osmAttribution, id: 'examples.map-i86knfo3'});
            map = new L.Map(map_element);
            osm.addTo(map);
            marker_options =  {icon: redIcon, popupContent : "asad"};

          } else {
            map = L.map(map_element, {
              crs: L.CRS.Simple,
              minZoom: -3
            });
            bounds = [xy(0, 0), xy(500 * gadget.options.ratio, 500)];

            L.imageOverlay(gadget.options.image, bounds).addTo(map);
            marker_options =  {icon: redIcon, draggable: true};
          }

          for (i = 0; i < marker_list.length; i += 1) {
            m = marker_list[i];
            marker_link = document.createElement("a");
            marker_link.href = url_list[i];
            marker_link.text = m.doc.title;
            marker_link.className = "ui-btn-map";
            marker_label = document.createElement("div");
            marker_label.appendChild(marker_link);

            marker_space = document.createElement("span");
            marker_space.innerHTML = " &nbsp;  &nbsp;   |  &nbsp; ";
            marker_space.className = "ui-btn-map";
            marker_label.appendChild(marker_space);

            marker_monitor_link = document.createElement("a");
            marker_monitor_link.target = "_blank";
            // Please update me, and compose the actuall url.
            marker_monitor_link.href = hateoas_url + marker_list[i].jio_key + "/Base_redirectToMonitor";
            marker_monitor_link.text = "   >   ";
            marker_monitor_link.className = "ui-btn-map ui-btn ui-btn-icon-left ui-icon-desktop";

            marker_label.appendChild(marker_monitor_link);

            marker = new L.marker(
              [m.doc.latitude || 0, m.doc.longitude || 0],
              marker_options
            )
            .addTo(map)
            .bindPopup(marker_label, {autoClose: false, closeOnClick: false});
            new_marker_list.push(marker);
            marker._index = i;
            marker._queue = new RSVP.Queue();
          }

          if (gadget.options.view_mode === undefined || gadget.options.view_mode === 'map') {
            if (latitude !== 0 || new_marker_list.length === 0) {
              map.setView(new L.LatLng(latitude, longitude), zoom);
            } else {
              group = new L.featureGroup(new_marker_list);
              map.fitBounds(group.getBounds());
            }
          } else {
            map.setView([250, 250], 1);
            for (i = 0; i < new_marker_list.length; i += 1) {
              new_marker_list[i].on('dragend', function (e) {
                return gadget.notifyChange();
              });
            }
          }

          gadget.props.new_marker_list = new_marker_list;
          list = [];
          for (i = 0; i < new_marker_list.length; i += 1) {
            new_marker_list[i].on('popupopen', function (e) {
              var index = e.target._index,
                tmp,
                container = e.popup._container.querySelector('.leaflet-popup-content-wrapper');
              tmp = container.querySelector('.sensor-status');
              if (!tmp) {
                tmp = document.createElement('div');
                tmp.className = 'sensor-status';
                tmp.style['min-width'] = '210px';
                container.appendChild(tmp);
                e.target._queue.push(function () {
                  return gadget.declareGadget('gadget_slapos_site_status.html', {
                    element: tmp
                  });
                })
                .push(function (computer) {
                  //xxxx repopup to resize popup
                  new_marker_list[index].openPopup();
                  return computer.render({value: {
                    jio_key : gadget.options.marker_list ? gadget.options.marker_list[index].jio_key : "",
                    doc: gadget.options.marker_list ? gadget.options.marker_list[index].doc : ""
                  }
                  });
                });
              }
            });
            new_marker_list[i].openPopup();
            list.push(new_marker_list[i]._queue);
          }
          return RSVP.all(list);
        });
    });
}(window, document, rJS, RSVP));