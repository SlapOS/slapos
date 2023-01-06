import {runPubsub} from "{{ qjs_wrapper }}";
import {Worker} from "os";

const PORT = "4840";
const IPV6 = "{{ ipv6 }}";

let parent = Worker.parent;

function handle_msg(e) {
  switch(e.data.action) {
    case "run":
      runPubsub(IPV6, PORT, "{{ net_if }}", e.data.id, e.data.interval, e.data.publish);
      parent.postMessage({running: false});
      parent.onmessage = null;
      break;
    default:
      console.log("Undefined action from parent: ", e.data.action);
  }
}

parent.onmessage = handle_msg;
