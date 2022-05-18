/*jslint indent2 */
/*global console */
{% set comma_separated_drone_id_list = ', '.join(drone_id_list.split()) -%}

import {
  arm,
  doParachute,
  getAltitude,
  getYaw,
  initPubsub,
  land,
  landed,
  loiter,
  start,
  setAltitude,
  setTargetCoordinates,
  stop,
  stopPubsub,
  takeOffAndWait,
  Drone
} from "{{ qjs_wrapper }}"; //jslint-quiet
import {sleep, SIGINT, SIGTERM, signal, Worker} from "os";
import {exit} from "std";

const IP    = "{{ autopilot_ip }}";
const PORT  = "7909";
const URL = "udp://" + IP + ":" + PORT;
const LOG_FILE  = "{{ log_dir }}/mavsdk-log";

const droneIdList = [{{ comma_separated_drone_id_list }}];
const droneDict = {};

const idToFollow = {{ id_to_follow }}

const ALTITUDE_DIFF = 50;
const EPSILON_YAW = 6;
const EPSILON_ALTITUDE = 2;
const TARGET_YAW = 0;

var pubsubRunning = false;
var pubsubWorker;

function connect() {
  exit_on_fail(start(URL, LOG_FILE, 60), "Failed to connect to " + URL);
}

function exit_on_fail(ret, msg) {
  if(ret) {
    console.log(msg);
    quit();
    exit(-1);
  }
}

function goToAltitude(target_altitude, wait, go) {
  if(go) {
    exit_on_fail(
      setAltitude(target_altitude),
      `Failed to go to altitude ${target_altitude} m`
    );
  }

  if(wait) {
    waitForAltitude(target_altitude);
  }
}

function land() {
  var yaw;

  while(true) {
    yaw = getYaw();
    console.log(`[DEMO] Waiting for yaw... (${yaw} , ${TARGET_YAW})`);
    if(Math.abs(yaw - TARGET_YAW) < EPSILON_YAW) {
      break;
    }
    sleep(250);
  }

  console.log("[DEMO] Deploying parachute...");
  exit_on_fail(doParachute(2), "Failed to deploy parachute");
}

function startPubsub() {
  pubsubWorker = new Worker("{{ pubsub_script }}");
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

  pubsubWorker.postMessage({ action: "run" });
  pubsubRunning = true;
  return 0;
}

function quit() {
  stop();
  if(pubsubRunning)
    stopPubsub()
}

function stopHandler(sign) {
  console.log("received ctrl-c");
  quit();
}

function waitForAltitude(target_altitude) {
  var altitude = getAltitude();
  while(Math.abs(altitude - target_altitude) > EPSILON_ALTITUDE) {
    console.log(
      `[DEMO] Waiting for altitude... (${altitude} , ${target_altitude})`);
    sleep(1000);
    altitude = getAltitude();
  }
}

(function() {
  const DEMO = false;
  const SIMULATION = {{ is_a_simulation }};

  var altitude;

  var LANDING_ALTITUDE = 150;
  var INITIAL_ALTITUDE = 210 + ALTITUDE_DIFF;

  if(DEMO) {
    LANDING_ALTITUDE = 105;
    INITIAL_ALTITUDE = 100 + ALTITUDE_DIFF;
  }
  signal(SIGINT, stopHandler);
  signal(SIGTERM, stopHandler);
  startPubsub();

  console.log("Will connect to", URL);

  console.log("[DEMO] Connecting...\n");
  connect();
  if(SIMULATION) {
    exit_on_fail(arm(), "Failed to arm");
    takeOffAndWait();
    goToAltitude(INITIAL_ALTITUDE + 1, true, true);
  }

  do {
    sleep(1000);
    altitude = getAltitude();
    console.log(
      `[DEMO] Waiting for altitude... (${altitude} , ${INITIAL_ALTITUDE})`);
  }
  while(altitude < INITIAL_ALTITUDE);

  console.log("[DEMO] Setting loiter mode...\n");
  loiter();
  sleep(1000);

  console.log("[DEMO] Switching to following mode...\n");
  while(droneDict[idToFollow].altitude > LANDING_ALTITUDE) {
    setTargetCoordinates(
      droneDict[idToFollow].latitude,
      droneDict[idToFollow].longitude,
      droneDict[idToFollow].altidute + ALTITUDE_DIFF,
      0
    );
  }

  console.log("[DEMO] Stop following...\n");
  console.log("[DEMO] Setting altitude...\n");
  goToAltitude(LANDING_ALTITUDE, true, true);

  console.log("[DEMO] Landing...\n");
  land();

  while(!landed()) {
    sleep(1000);
  }
  quit();
})();
