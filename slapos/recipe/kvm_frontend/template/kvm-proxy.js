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

isRawIPv6 = function checkipv6(str) {
  // Inspired by http://forums.intermapper.com/viewtopic.php?t=452
  return (/^\s*((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))(%.+)?\s*$/.test(str));
}(listenInterface);

// Dummy middleware that throws 404 not found.
var middlewareNotFound = function(req, res, proxy) {
  res.statusCode = 404;
  res.setHeader('Content-Type', 'text/plain');
  res.end('This URL is not known. Please check your URL or contact your ' +
      'SlapOS administrator.');
};
middlewareNotFound.proxyWebSocketRequest = function(req, socket, head, next) {
  console.log('stop');
  socket.end();
};

/**
 * Rewrite URL to match Zope's virtual host monster if we use vifib
 */
var middlewareVifib = function(req, res, next) {
  // Completely hardcoded rewrite
  var vifibPrefix = '/hosting';
  if (req.url.indexOf(vifibPrefix) == 0) {
    // Rewrite URL to match virtual host
    req.url = vifibPrefix + '/VirtualHostBase/https/' + req.headers.host +
              '/erp5/web_site_module/VirtualHostRoot' + req.url;
    console.log('Vifib rewrite. New URL is : ' + req.url);
  }
  next();
};

/**
 * Create server
 */
var proxyServer = httpProxy.createServer(
  middlewareVifib,
  // We declare our proxyByUrl middleware
  proxyByUrl(proxyTable),
  // Then we add your dummy middleware, called when proxyByUrl doesn't find url.
  middlewareNotFound,
  // And we set HTTPS options for server. HTTP will be forbidden.
  {
    https: {
      key: fs.readFileSync(
        //'/Users/cedricdesaintmartin/Desktop/SlapOS/slapconsole-keys/cedric-owf-0/ssl.key',
        sslKeyFile,
        'utf8'
      ),
      cert: fs.readFileSync(
        //'/Users/cedricdesaintmartin/Desktop/SlapOS/slapconsole-keys/cedric-owf-0/ssl.cert',
        sslCertFile,
        'utf8'
      )
    },
    source: {
    host: listenInterface,
    port: port
  }}
);

// We gonna rock this civilization.
proxyServer.listen(port, listenInterface);
console.log('HTTPS server started and listening at ' + listenInterface + ':' +
            port);

// Dummy HTTP server redirecting to HTTPS. Only has sense if we can use port 80
if (redirect = '1') {
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
    console.log('HTTP redirect server started and listening at ' +
                listenInterface + ':' + httpPort);
  } catch (EACCES) {
    console.log('Couldn\'t start plain HTTP redirection server : ' + EACCESS)
  }
}
