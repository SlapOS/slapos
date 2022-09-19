import {runPubsub} from {{ json_module.dumps(qjs_wrapper) }};
import {Worker} from "os";
import {open} from "std";

const CONF_PATH = {{ json_module.dumps(configuration) }},
  PORT = "4840";

let parent = Worker.parent;

var conf_file = open(CONF_PATH, "r");
const configuration = JSON.parse(conf_file.readAsString());
conf_file.close();

function handle_msg(e) {
  switch(e.data.action) {
    case "run":
      runPubsub(configuration.multicastIp, PORT, configuration.netIf, e.data.id, e.data.interval, e.data.publish);
      parent.postMessage({running: false});
      parent.onmessage = null;
      break;
    default:
      console.log("Undefined action from parent: ", e.data.action);
  }
}

parent.onmessage = handle_msg;
