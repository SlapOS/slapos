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

var listenInterfacev6 = process.argv[2],
    listenInterfacev4 = process.argv[3],
    port = process.argv[4],
    sslKeyFile = process.argv[5],
    sslCertFile = process.argv[6],
    proxyTable = process.argv[7],
    redirect = process.argv[8] || false,
    isRawIPv6;

if (process.argv.length < 7) {
    console.error("Too few arguments. Exiting.");
  process.exit(1);
}

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
var proxyServerv6 = httpProxy.createServer(
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
    host: listenInterfacev6,
    port: port
  }}
);


var proxyServerv4 = httpProxy.createServer(
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
    host: listenInterfacev4,
    port: port
  }}
);


console.log('HTTPS server starting and trying to listen on ' +
            listenInterfacev4 + ':' + port);
// Release the beast.
proxyServerv6.listen(port, listenInterfacev6);
proxyServerv4.listen(port, listenInterfacev4);

// Dummy HTTP server redirecting to HTTPS. Only has sense if we can use port 80
if (redirect === '1') {
  console.log('HTTP redirect server starting and trying to listen on ' +
              listenInterface + ':' + httpPort);
/*   
*try {
*    var httpPort = 80;
*    http.createServer(function(req, res) {
*      var url;
*      if (isRawIPv6 === true) {
*        url = 'https://[' + listenInterface + ']';
*      } else {
*        url = 'https://' + listenInterface;
*      }
*      // If non standard port : need to specify it
*      if (port !== 443) {
*        url = url + ':' + port;
*      }
*      // Add last part of URL
*      url = url + req.url;
*      console.log(url);
*      // Anwser "permanently redirected"
*      res.statusCode = 301;
*      res.setHeader('Location', url);
*      res.end();
*    }).listen(httpPort, listenInterface);
*  } catch (error) {
*    console.log('Couldn\'t start plain HTTP redirection server : ' + error)
*  }
*/
}
