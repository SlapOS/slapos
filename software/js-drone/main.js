/* global console */
import {
  arm,
  start,
  stop,
  stopPubsub,
  takeOffAndWait
} from "{{ qjs_wrapper }}";
import { setTimeout, Worker } from "os";
import { readAsString, exit } from "std";

(function (console, setTimeout, Worker) {
  "use strict";
  const configuration = JSON.parse(std.readAsString({{ configuration }}),
    URL = "udp://" + configuration.autopilot-ip + ":7909",
    LOG_FILE = "{{ log_dir }}/mavsdk-log";

  // Use a Worker to ensure the user script
  // does not block the main script
  // (preventing it to be stopped for example)

  // Create the update loop in the main script
  // to prevent it to finish (and so, exit the quickjs process)
  var pubsubWorker,
    pubsubRunning = false,
    worker = new Worker("{{ worker_script }}"),
    user_script = scriptArgs[1],
    // Use the same FPS than browser's requestAnimationFrame
    FPS = 1000 / 60,
    previous_timestamp,
    can_update = false;

  function connect() {
    console.log("Will connect to", URL);
    exitOnFail(start(URL, LOG_FILE, 60), "Failed to connect to " + URL);
  }

  function exitOnFail(ret, msg) {
    if (ret) {
      console.log(msg);
      quit(1);
    }
  }

  function quit(exit_code) {
    stop();
    if(pubsubRunning) {
      stopPubsub();
    }
    exit(exit_code);
  }

  if (configuration.is-publisher) {
    console.log("Connecting to aupilot\n");
    connect();
  }

  pubsubWorker = new Worker("{{ pubsub_script }}");
  pubsubWorker.onmessage = function(e) {
    if (!e.data.publishing) {
      pubsubWorker.onmessage = null;
    }
  }

  worker.postMessage({type: "initPubsub"});

  function takeOff() {
    exitOnFail(arm(), "Failed to arm");
    takeOffAndWait();
  }

  function load() {
    if (configuration.is-publisher && configuration.is-a-simulation) {
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
    let timestamp = Date.now(),
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
        timeout = Math.min(FPS, FPS - (timestamp - previous_timestamp - FPS));
        previous_timestamp = timestamp;
      } else {
        timeout = FPS - (timestamp - previous_timestamp);
      }
    } else {
      // If timeout occurs, but update is not yet finished
      // wait a bit
      timeout = FPS / 4;
    }
    // Ensure loop is not done with timeout < 1
    // Otherwise, it will goes crazy for 1 second
    setTimeout(loop, Math.max(1, timeout));
  }

  worker.onmessage = function (e) {
    let type = e.data.type;
    if (type === 'initialized') {
      pubsubWorker.postMessage({
        action: "run",
        id: configuration.id,
        interval: FPS,
        publish: configuration.is-publisher
      });
      pubsubRunning = true;
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
      if (configuration.is-publisher) {
        quit(e.data.exit);
      } else {
        stopPubsub();
        exit(e.data.exit);
      }
    } else {
      console.log('Unsupported message type', type);
      quit(1);
    }
  };
}(console, setTimeout, Worker));
