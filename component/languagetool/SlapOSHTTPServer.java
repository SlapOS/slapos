package org.languagetool.server;

// Starts LanguageTool's HTTP server bound to a single address.
// Lives in package org.languagetool.server because
// HTTPServerConfig(String[]) and DatabaseAccess.init() are package-private.
class SlapOSHTTPServer {
  public static void main(String[] args) throws Exception {
    String host = System.getProperty("languagetool.host");
    if (host == null) {
      throw new IllegalArgumentException("-Dlanguagetool.host=<bind address> is required");
    }
    HTTPServerConfig config = new HTTPServerConfig(args);
    DatabaseAccess.init(config);
    new HTTPServer(config, false, host, null).run();
  }
}
