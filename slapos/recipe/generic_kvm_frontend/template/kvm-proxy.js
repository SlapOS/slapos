/*****************************************************************************
*
* Copyright (c) 2012 Vifib SARL and Contributors. All Rights Reserved.
*
* WARNING: This program as such is intended to be used by professional
* programmers who take the whole responsibility of assessing all potential
* consequences resulting from its eventual inadequacies and bugs
* End users who are looking for a ready-to-use solution with commercial
* guarantees and support are strongly adviced to contract a Free Software
* Service Company
*
* This program is Free Software; you can redistribute it and/or
* modify it under the terms of the GNU General Public License
* as published by the Free Software Foundation; either version 3
* of the License, or (at your option) any later version.
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with this program; if not, write to the Free Software
* Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
*
*****************************************************************************/

/* Wrapper used to configure the httpproxy node package to proxy
   http://myhost/myinstance
   to real IP/URL of myinstance
*/

var fs = require('fs'),
    util = require('util'),
    colors = require('colors'),
    http = require('http'),
    httpProxy = require('http-proxy'),
    proxyByUrl = require('proxy-by-url');

var listenInterface = process.argv[2],
    port = process.argv[3],
    sslKeyFile = process.argv[4],
    sslCertFile = process.argv[5],
    proxyTable = process.argv[6],
    redirect = process.argv[7] || false,
    isRawIPv6;

if (process.argv.length < 7) {
    console.error("Too few arguments. Exiting.");
  process.exit(1);
}

isRawIPv6 = function checkipv6(str) {
  // Inspired by http://forums.intermapper.com/viewtopic.php?t=452
  return (/^\s*((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))(%.+)?\s*$/.test(str));
}(listenInterface);

/**
 * Dummy middleware that throws 404 not found. Does not contain websocket
 * middleware.
 */
var middlewareNotFound = function(req, res, proxy) {
  res.statusCode = 404;
  res.setHeader('Content-Type', 'text/plain');
  res.end('This URL is not known. Please check your URL or contact your ' +
      'SlapOS administrator.');
};

/**
 * Create server
 */
var proxyServer = httpProxy.createServer(
  // We declare our proxyByUrl middleware
  proxyByUrl(proxyTable),
  // Then we add your dummy middleware, called when proxyByUrl doesn't find url.
  middlewareNotFound,
  // And we set HTTPS options for server. HTTP will be forbidden.
  {
    https: {
      key: fs.readFileSync(
        sslKeyFile,
        'utf8'
      ),
      cert: fs.readFileSync(
        sslCertFile,
        'utf8'
      )
    },
    source: {
    host: listenInterface,
    port: port
  }}
);

console.log('HTTPS server starting and trying to listen on ' +
            listenInterface + ':' + port);
// Release the beast.
proxyServer.listen(port, listenInterface);

// Dummy HTTP server redirecting to HTTPS. Only has sense if we can use port 80
if (redirect === '1') {
  console.log('HTTP redirect server starting and trying to listen on ' +
              listenInterface + ':' + httpPort);
  try {
    var httpPort = 80;
    http.createServer(function(req, res) {
      var url;
      if (isRawIPv6 === true) {
        url = 'https://[' + listenInterface + ']';
      } else {
        url = 'https://' + listenInterface;
      }
      // If non standard port : need to specify it
      if (port !== 443) {
        url = url + ':' + port;
      }
      // Add last part of URL
      url = url + req.url;
      console.log(url);
      // Anwser "permanently redirected"
      res.statusCode = 301;
      res.setHeader('Location', url);
      res.end();
    }).listen(httpPort, listenInterface);
  } catch (error) {
    console.log('Couldn\'t start plain HTTP redirection server : ' + error)
  }
}
