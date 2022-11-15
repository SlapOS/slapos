/*jslint nomen: true, indent: 2, maxerr: 3, maxlen: 80 */
/*global console, open, runPubsub, Worker*/
import {runPubsub} from {{ json_module.dumps(qjs_wrapper) }};
import {Worker} from "os";
import {open} from "std";

(function (console, open, runPubsub, Worker) {
  "use strict";

  var CONF_PATH = {{ json_module.dumps(configuration) }},
    PORT = "4840",
    parent = Worker.parent,
    conf_file = open(CONF_PATH, "r"),
    configuration = JSON.parse(conf_file.readAsString());
  conf_file.close();

  function handle_msg(e) {
    switch (e.data.action) {
    case "run":
      runPubsub(
        configuration.multicastIp,
        PORT,
        configuration.netIf,
        e.data.id,
        e.data.interval,
        e.data.publish
      );
      parent.postMessage({running: false});
      parent.onmessage = null;
      break;
    default:
      console.log("Undefined action from parent: ", e.data.action);
    }
  }

  parent.onmessage = handle_msg;
}(console, open, runPubsub, Worker));