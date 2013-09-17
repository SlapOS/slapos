/*****************************************************************************
*
* Copyright (c) 2013 Vifib SARL and Contributors. All Rights Reserved.
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

var fs = require('fs'),
    util = require('util'),
    colors = require('colors'),
    http = require('http'),
    httpProxy = require('http-proxy');


var listenInterface = process.argv[2],
    port = process.argv[3],
    sslKeyFile = process.argv[4],
    sslCertFile = process.argv[5],
    backendIp = process.argv[6],
    backendPort = process.argv[7];

if (process.argv.length < 8) {
  console.error("Too few arguments. Exiting.");
  process.exit(1);
}

var middleware = function (req, res, proxy) {
  return proxy.proxyRequest(req, res,{
    host: backendIp,
    port: backendPort
  });
};

middleware.proxyWebSocketRequest = function (req, socket, head, proxy) {
  return proxy.proxyWebSocketRequest(req, socket, head,{
    host: backendIp,
    port: backendPort
  });
};

/**
 * Create server
 */
var proxyServer = httpProxy.createServer(
  middleware,
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
