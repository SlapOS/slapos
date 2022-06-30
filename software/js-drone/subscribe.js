/*jslint-disable*/
{% set comma_separated_drone_id_list = ', '.join(drone_id_list.split()) -%}
/*jslint-enable*/

import {
  initPubsub,
  stopPubsub,
  Drone
} from "{{ qjs_wrapper }}"; //jslint-quiet
import {Worker} from "os";
/*jslint-disable*/
import * as std from "std";
/*jslint-enable*/

const droneIdList = [{{ comma_separated_drone_id_list }}];
const droneDict = {};

var pubsubWorker = new Worker("{{ pubsub_script }}");
pubsubWorker.onmessage = function(e) {
  if (!e.data.publishing)
    pubsubWorker.onmessage = null;
}

initPubsub(droneIdList.length);
for (let i = 0; i < droneIdList.length; i++) {
  let id = droneIdList[i]
  droneDict[id] = new Drone(id);
  droneDict[id].init(i);
}

pubsubWorker.postMessage({ action: "run", publish: false });

const f = std.fdopen(std.in, "r");
console.log("Use q to quit");
while (f.getline() != "q") {
  continue;
}

stopPubsub();
f.close();
