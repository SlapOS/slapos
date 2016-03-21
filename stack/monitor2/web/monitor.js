/*jslint indent:2 */
(function () {
  "use strict";

  var monitor_title = 'Monitoring interface',
    RSS_ICON_DATA_URI = [
      "data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIj8+CjwhRE9DVFlQR",
      "SBzdmcgUFVCTElDICItLy9XM0MvL0RURCBTVkcgMS4xLy9FTiIgImh0dHA6Ly93d3cu",
      "dzMub3JnL0dyYXBoaWNzL1NWRy8xLjEvRFREL3N2ZzExLmR0ZCI+CjxzdmcgeG1sbnM",
      "9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB2ZXJzaW9uPSIxLjEiIHdpZHRoPS",
      "IxMjhweCIgaGVpZ2h0PSIxMjhweCIgdmlld0JveD0iMCAwIDI1NiAyNTYiPgo8cmVjd",
      "CB3aWR0aD0iMjU2IiBoZWlnaHQ9IjI1NiIgeD0iMCIgIHk9IjAiICBmaWxsPSIjRjQ5",
      "QzUyIi8+CjxjaXJjbGUgY3g9IjY4IiBjeT0iMTg5IiByPSIyNCIgZmlsbD0iI0ZGRiI",
      "vPgo8cGF0aCBkPSJNMTYwIDIxM2gtMzRhODIgODIgMCAwIDAgLTgyIC04MnYtMzRhMT",
      "E2IDExNiAwIDAgMSAxMTYgMTE2eiIgZmlsbD0iI0ZGRiIvPgo8cGF0aCBkPSJNMTg0I",
      "DIxM0ExNDAgMTQwIDAgMCAwIDQ0IDczIFYgMzhhMTc1IDE3NSAwIDAgMSAxNzUgMTc1",
      "eiIgZmlsbD0iI0ZGRiIvPgo8L3N2Zz4K"
    ].join("");

  function loadJson(url) {
    /*global XMLHttpRequest */
    return new Promise(function (resolve, reject) {
      var xhr = new XMLHttpRequest();
      xhr.onload = function (event) {
        var response = event.target;
        if (response.status < 400) {
          try {
            var data = ( response.responseType === 'text' || response.responseType === '') ? JSON.parse(response.responseText) : response.response;
            resolve(data);
          } catch (e) {
            reject(e);
          }
        } else {
          reject(new Error("XHR: " + response.status + ": " + response.statusText));
        }
      };
      xhr.onerror = function () {
        reject(new Error("XHR: Error"));
      };
      xhr.open("GET", url, true);
      xhr.send();
    });
  }

  ///////////////////
  // tools for HAL //

  function getProperty(object, path) {
    if (Array.isArray(path)) {
      while (path.length) {
        object = object[path.shift()];
      }
    } else {
      return object[path];
    }
    return object;
  }

  function softGetProperty(object, path) {
    try {
      return getProperty(object, path);
    } catch (ignored) {
      return undefined;
    }
  }

  function forceList(value) {
    if (Array.isArray(value)) {
      return value;
    }
    return [value];
  }

  function softGetPropertyAsList(object, path) {
    try {
      return forceList(getProperty(object, path));
    } catch (ignored) {
      return [];
    }
  }

  ///////////////////

  function htmlToElementList(html) {
    /*global document */
    var div = document.createElement("div");
    div.innerHTML = html;
    return div.querySelectorAll("*");
  }

  function resolveUrl(firstUrl) {
    /*jslint plusplus: true */
    /*global URL, location */
    var l = arguments.length, i = 1, url = new URL(firstUrl, location.href);
    while (i < l) { url = new URL(arguments[i++], url); }
    return url.href;
  }

  function joinUrl(url, path) {
    if (path && path[0] === '/') {
      path = path.slice(1);
    }
    if (url.indexOf('/', url.length - 1) === -1) {
      return url + '/' + path;
    }
    return url + escapeHtml(path);
  }

  function escapeHtml(html) {
    return html.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&apos;");
  }

  function loadAndRenderMonitorSection(root, monitor_dict, monitor_url) {
    var table, service_list = softGetPropertyAsList(monitor_dict, ["_embedded", "service"]);
    if (!service_list) {
      root.textContent = "";
      return;
    }
    table = document.createElement("table");
    table.className = "monitor-section";
    root.appendChild(table);
    return Promise.all(service_list.map(function (service_dict) {
      var interface_url = softGetProperty(service_dict, ["_links", "interface", "href"]),
        status_url = softGetProperty(service_dict, ["_links", "status", "href"]),
        href_html_part = (interface_url ? " href=\"" + escapeHtml(interface_url) + "\"" : ""),
        title_html_part = (service_dict.title ? escapeHtml(service_dict.title) : (service_dict.id ||"Untitled")),
        row = htmlToElementList("<table><tbody><tr><td><a" + href_html_part + ">" + title_html_part + "</a></td><td>Loading status...</td><td><a" + href_html_part + "><div style=\"height: 10mm; width: 10mm; background-color: gray;\"></div></a></td></tr></tbody></table>");
      table.appendChild(row[2]);
      if (!status_url) {
        row[5].textContent = "No status";
        return;
      }
      var full_status_url = (monitor_url === undefined) ? resolveUrl(monitor_url, status_url): joinUrl(monitor_url, status_url);
      return loadJson(full_status_url).then(function (status_dict) {
        if (status_dict.description) {
          row[2].title = status_dict.description;
        }
        row[5].textContent = status_dict.message || "";
        row[8].style.backgroundColor = status_dict.status === "OK" ? "green" : "red";
      }).catch(function (reason) {
        row[5].textContent = (reason && (reason.name + ": " + reason.message));
        row[8].style.backgroundColor = "red";
      });
    }));
  }

  function loadAndRenderMonitorJson(root) {
    root.textContent = "Loading monitor section...";
    return loadJson("monitor.haljson").then(function (monitor_dict) {
      //monitor_json_list.push(monitor_dict);
      root.innerHTML = "";
      var loading = loadAndRenderMonitorSection(root, monitor_dict), related_monitor_list = softGetPropertyAsList(monitor_dict, ["_links", "related_monitor"]);
      if (!related_monitor_list.length) { return loading; }
      return Promise.all([loading, Promise.all(related_monitor_list.map(function (link) {
        var div = htmlToElementList("<div>Loading monitor section...</div>")[0];
        root.appendChild(div);
        if (link.href[link.href.length - 1] !== "/") {
          link.href += "/";
        }
        var haljson_link = resolveUrl(link.href, "monitor.haljson");
        return loadJson(haljson_link).catch(function (reason) {
          div.textContent = (reason && (reason.name + ": " + reason.message));
        }).then(function (monitor_dict) {
          //monitor_json_list.push(monitor_dict);
          div.remove();
          return loadAndRenderMonitorSection(root, monitor_dict, link.href);
        });
      }))]);
    });
  }

  function bootstrap(root) {
    var element_list = htmlToElementList([
      "<header>",
      "  <a href=\"\" class=\"as-button\">Refresh</a>",
      "  <a href=\"/logout.html\" class=\"as-button\">Logout</a>",
      "  <a href=\"/feed\"><img src=\"" + RSS_ICON_DATA_URI + "\" style=\"width: 10mm; height: 10mm; vertical-align: middle;\" alt=\"[RSS Feed]\" /></a>",
      "</header>",
      "<h1>" + monitor_title + "</h1>",
      "<h2>System health status</h2>",
      "<p>This interface allow to see the status of several features, it may show problems and sometimes provides a way to fix them.</p>",
      "<p>Red square means the feature has a problem, green square means it is ok.</p>",
      "<p>You can click on a feature below to get more precise information.</p>"
    ].join("\n")), div = document.createElement("div"), tmp;
    [].reduce.call(element_list, function (array, element) {
      if (element.parentNode.parentNode) { return array; }
      array.push(element);
      return array;
    }, []).forEach(function (element) {
      root.appendChild(element);
    });
    document.title = monitor_title;
    root.appendChild(div);
    /*global alert */
    tmp = loadAndRenderMonitorJson(div);
    tmp.catch(alert);
    /*global console */
    tmp.catch(console.error.bind(console));
  }

  /*global setTimeout */
  setTimeout(function () {
    /*global document */
    bootstrap(document.body);
  });
}());
