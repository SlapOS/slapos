/*jslint-disable*/
{% set comma_separated_drone_id_list = ', '.join(drone_id_list.split()) -%}
/*jslint-enable*/

import {
  arm,
  doParachute,
  getAltitude,
  getLatitude,
  getLongitude,
  getYaw,
  initPubsub,
  setAltitude,
  setTargetLatLong,
  start,
  stop,
  stopPubsub,
  takeOffAndWait,
  Drone
} from "{{ qjs_wrapper }}"; //jslint-quiet
import {exit} from "std";
import {sleep, Worker} from "os";

const IP = "{{ autopilot_ip }}";
const PORT = "7909";

export const IS_LEADER = {{ is_leader }};
export const LEADER_ID = {{ leader_id }};
export const SIMULATION = {{ is_a_simulation }};

export const EPSILON = 105;
const EPSILON_YAW = 6;
const EPSILON_ALTITUDE = 5;
const TARGET_YAW = 0;
export const ALTITUDE_DIFF = 30;

const URL = "udp://" + IP + ":" + PORT;
const LOG_FILE = "{{ log_dir }}/mavsdk-log";

const droneIdList = [{{ comma_separated_drone_id_list }}];
const droneDict = {};

var pubsubRunning = false;
var pubsubWorker;

export function connect() {
  console.log("Will connect to", URL);
  exit_on_fail(start(URL, LOG_FILE, 60), "Failed to connect to " + URL);
}

export function distance(lat1, lon1, lat2, lon2) {
  const R = 6371e3; // meters
  const la1 = lat1 * Math.PI/180; // la, lo in radians
  const la2 = lat2 * Math.PI/180;
  const lo1 = lon1 * Math.PI/180;
  const lo2 = lon2 * Math.PI/180;

  //haversine formula
  const sinLat = Math.sin((la2 - la1)/2);
  const sinLon = Math.sin((lo2 - lo1)/2);
  const h = sinLat*sinLat + Math.cos(la1)*Math.cos(la2)*sinLon*sinLon
  return 2*R*Math.asin(Math.sqrt(h));
}

export function displayDronePositions() {
  if(!pubsubRunning)
    console.log("You must start pubsub first !");
  else {
    for (const [id, drone] of Object.entries(droneDict)) {
      console.log(id, drone.latitude, drone.longitude, drone.altitudeAbs, drone.altitudeRel);
    }
  }
  return 0;
}

function exit_on_fail(ret, msg) {
  if(ret) {
    console.log(msg);
    quit();
    exit(-1);
  }
}

export function quit() {
  stop();
  if(pubsubRunning) {
    stopPubsub();
  }
}

export function goToAltitude(target_altitude, wait, go) {
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

export function land() {
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

export function setLatLong(latitude, longitude, target_altitude) {
  var cur_latitude;
  var cur_longitude;
  var d;

  if(target_altitude !== 0) {
    setAltitude(target_altitude, false, true);
  }

  console.log(`Going to (${latitude}, ${longitude}) from
                (${getLatitude()}, ${getLongitude()})`);
  exit_on_fail(
    setTargetLatLong(latitude, longitude),
    `Failed to go to (${latitude}, ${longitude})`
  );
  sleep(500);

  while(true) {
    cur_latitude = getLatitude();
    cur_longitude = getLongitude();
    d = distance(cur_latitude, cur_longitude, latitude, longitude);
    console.log(`Waiting for drone to get to destination (${d} m),
    (${cur_latitude} , ${cur_longitude}), (${latitude}, ${longitude})`);
    if(d < EPSILON) {
      sleep(6000);
      return;
    }
    sleep(1000);
  }
}

export function startPubsub() {
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

  pubsubWorker.postMessage({ action: "run", publish: true });
  pubsubRunning = true;
  return droneDict;
}

export function takeOff(altitude) {
  exit_on_fail(arm(), "Failed to arm");
  takeOffAndWait();
  goToAltitude(altitude, true, true);
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
