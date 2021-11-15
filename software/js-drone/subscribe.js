/*jslint indent2 */

import { subscribe } from "{{ qjs_wrapper }}"; //jslint-quiet
import { Worker } from "os";

const PORT = "4840";
const IPV6 = "{{ ipv6 }}";

subscribe(IPV6, PORT);
Worker.parent.postMessage("Pubsub subscription finished");
