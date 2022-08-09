/*global console*/
import {
  arm,
  start,
  stop,
  stopPubsub,
  takeOffAndWait
} from "{{ qjs_wrapper }}";
import { setTimeout, Worker } from "os";
import { exit } from "std";

(function (console, setTimeout, Worker) {
  "use strict";
  const IP = "{{ autopilot_ip }}",
    URL = "udp://" + IP + ":7909",
    LOG_FILE = "{{ log_dir }}/mavsdk-log",
    IS_A_DRONE = {{ 'true' if is_a_drone else 'false' }},
    SIMULATION = {{ 'true' if is_a_simulation else 'false' }};

  // Use a Worker to ensure the user script
  // does not block the main script
  // (preventing it to be stopped for example)

  // Create the update loop in the main script
  // to prevent it to finish (and so, exit the quickjs process)
  var pubsubWorker,
    worker = new Worker("{{ worker_script }}"),
    user_script = scriptArgs[1],
    // Use the same FPS than browser's requestAnimationFrame
    FPS = 1000 / 60,
    previous_timestamp,
    can_update = false,
    i = 0;

  function connect() {
    console.log("Will connect to", URL);
    exit_on_fail(start(URL, LOG_FILE, 60), "Failed to connect to " + URL);
  }

  function exit_on_fail(ret, msg) {
    if (ret) {
      console.log(msg);
      quit(1);
    }
  }

  function quit(is_a_drone, exit_code) {
    if (is_a_drone) {
      stop();
    }
    stopPubsub();
    exit(exit_code);
  }

  if (IS_A_DRONE) {
    console.log("Connecting to aupilot\n");
    connect();
  }

  pubsubWorker = new Worker("{{ pubsub_script }}");
  pubsubWorker.onmessage = function(e) {
    if (!e.data.publishing)
      pubsubWorker.onmessage = null;
  }

  worker.postMessage({type: "initPubsub"});

  function takeOff() {
    exit_on_fail(arm(), "Failed to arm");
    takeOffAndWait();
  }

  function load() {
    if (IS_A_DRONE && SIMULATION) {
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
        id: {{ id }},
        publish: IS_A_DRONE
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
      quit(IS_A_DRONE, e.data.exit);
    } else {
      console.log('Unsupported message type', type);
      quit(IS_A_DRONE, 1);
    }
  };
}(console, setTimeout, Worker));
