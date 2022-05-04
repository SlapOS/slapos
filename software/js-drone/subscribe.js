/*jslint indent2 */
import { subscribe } from "{{ qjs_wrapper }}"; //jslint-quiet
import { Worker } from "os";

const PORT = "4840";
const IPV6 = "{{ ipv6 }}";

var parent = Worker.parent;

function handle_msg(e) {
  switch(e.data.action) {
    case "subscribe":
      subscribe(IPV6, PORT);
      parent.postMessage({ subscribing: false});
      parent.onmessage = null;
      break;
    default:
      console.log("Undefined action from parent: ", e.data.action);
  }
}

parent.onmessage = handle_msg;
