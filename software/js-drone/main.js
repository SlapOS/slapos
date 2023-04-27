/*jslint nomen: true, indent: 2, maxerr: 3, maxlen: 80 */
/*global arm, console, exit, open, scriptArgs, setTimeout, start, stop,
  stopPubsub, takeOffAndWait, Worker*/
import {
  arm,
  start,
  stop,
  stopPubsub,
  takeOffAndWait
} from {{ json_module.dumps(qjs_wrapper) }};
import { setTimeout, Worker } from "os";
import { open, exit } from "std";

(function (arm, console, exit, open, scriptArgs, setTimeout, start, stop,
           stopPubsub, takeOffAndWait, Worker) {
  "use strict";

  var CONF_PATH = {{ json_module.dumps(configuration) }},
    conf_file = open(CONF_PATH, "r"),
    configuration = JSON.parse(conf_file.readAsString()),
    LOG_FILE = "{{ log_dir }}/mavsdk-log",
    pubsubWorker,
    worker,
    user_script = scriptArgs[1],
    FPS = 50, // Minimum sampling interval for open62541 monitored items
    previous_timestamp,
    can_update = false;

  conf_file.close();

  // Use a Worker to ensure the user script
  // does not block the main script
  // (preventing it to be stopped for example)

  // Create the update loop in the main script
  // to prevent it to finish (and so, exit the quickjs process)
  worker = new Worker("{{ worker_script }}");

  function quit(is_a_drone, shutdown, exit_code) {
    stopPubsub();
    if (is_a_drone) {
      stop(shutdown);
    }
    exit(exit_code);
  }

  function exitOnFail(ret, msg) {
    if (ret) {
      console.log(msg);
      quit(1);
    }
  }

  function connect() {
    var address = configuration.autopilotIp + ":" + configuration.autopilotPort;
    console.log("Will connect to", address);
    exitOnFail(
      start(configuration.autopilotIp, configuration.autopilotPort, LOG_FILE, 60),
      "Failed to connect to " + address
    );
  }

  if (configuration.isADrone) {
    console.log("Connecting to aupilot\n");
    connect();
  }

  pubsubWorker = new Worker("{{ pubsub_script }}");
  pubsubWorker.onmessage = function (e) {
    if (!e.data.publishing) {
      pubsubWorker.onmessage = null;
    }
  };

  worker.postMessage({type: "initPubsub"});

  function takeOff() {
    exitOnFail(arm(), "Failed to arm");
    takeOffAndWait();
  }

  function load() {
    if (configuration.isADrone && configuration.isASimulation) {
      takeOff();
    }

    // First argument must provide the user script path
    if (user_script === undefined) {
      console.log('Please provide the user_script path.');
      quit(1);
    }

    worker.postMessage({
      type: "load",
      path: user_script
    });
  }

  function loop() {
    var timestamp = Date.now(),
      timeout;
    if (can_update) {
      if (FPS <= (timestamp - previous_timestamp)) {
        // Expected timeout between every update
        can_update = false;
        worker.postMessage({
          type: "update",
          timestamp: timestamp
        });
        // Try to stick to the expected FPS
        timeout = FPS - (timestamp - previous_timestamp - FPS);
        previous_timestamp = timestamp;
      } else {
        timeout = FPS - (timestamp - previous_timestamp);
      }
    } else {
      // If timeout occurs, but update is not yet finished
      // wait a bit
      timeout = FPS / 4;
    }
    // Ensure loop is not done with timeout < 1ms
    setTimeout(loop, Math.max(1, timeout));
  }

  worker.onmessage = function (e) {
    var type = e.data.type;
    if (type === 'initialized') {
      pubsubWorker.postMessage({
        action: "run",
        id: configuration.id,
        interval: FPS,
        publish: configuration.isADrone
      });
      load();
    } else if (type === 'loaded') {
      previous_timestamp = -FPS;
      can_update = true;
      // Start the update loop
      loop();
    } else if (type === 'updated') {
      can_update = true;
    } else if (type === 'exited') {
      worker.onmessage = null;
      quit(configuration.isADrone, !configuration.isASimulation, e.data.exit);
    } else {
      console.log('Unsupported message type', type);
      quit(configuration.isADrone, !configuration.isASimulation, 1);
    }
  };
}(arm, console, exit, open, scriptArgs, setTimeout, start, stop, stopPubsub, 
  takeOffAndWait, Worker));
