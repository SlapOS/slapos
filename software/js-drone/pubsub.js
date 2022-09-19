import {runPubsub} from "{{ qjs_wrapper }}";
import {Worker} from "os";
import {readAsString} from "std";

const PORT = "4840",
  configuration = JSON.parse(readAsString({{ configuration }});

let parent = Worker.parent;

function handle_msg(e) {
  switch(e.data.action) {
    case "run":
      runPubsub(IPV6, PORT, configuration.multicast-ip, e.data.id, e.data.interval, e.data.publish);
      parent.postMessage({running: false});
      parent.onmessage = null;
      break;
    default:
      console.log("Undefined action from parent: ", e.data.action);
  }
}

parent.onmessage = handle_msg;
