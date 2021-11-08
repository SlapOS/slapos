/*jslint indent2 */
/*global console */

import {
  arm,
  doParachute,
  getAltitude,
  getInitialAltitude,
  getInitialLatitude,
  getInitialLongitude,
  getLatitude,
  getLongitude,
  getTakeOffAltitude,
  getYaw,
  landed,
  loiter,
  start,
  setAltitude,
  setTargetLatLong,
  stop,
  stopPubsub,
  takeOffAndWait
} from "{{ qjs_wrapper }}"; //jslint-quiet
import {sleep, Worker} from "os";
import {exit} from "std";

const IP    = "{{ autopilot_ip }}";
const PORT  = "7909";
const URL = "udp://" + IP + ":" + PORT;
const LOG_FILE  = "{{ log_dir }}/mavsdk-log";

const EPSILON = 105;
const EPSILON_YAW = 6;
const EPSILON_ALTITUDE = 2;
const TARGET_YAW = 0;

var publishing = false;
var worker;

function connect() {
  exit_on_fail(start(URL, LOG_FILE, 60), "Failed to connect to " + URL);
}

function distance(lat1, lon1, lat2, lon2) {
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

function exit_on_fail(ret, msg) {
  if(ret) {
    console.log(msg);
    if(publishing) {
      stopPubsub();
    }
    exit(-1);
  }
}

function goToAltitude(target_altitude, wait, go) {
  var altitude;

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

function publish() {
  worker = new Worker("{{ publish_script }}");
  worker.onmessage = function(e) {
    if(!e.data.publishing) {
      worker.onmessage = null;
    }
  }
  worker.postMessage({ action: "publish" });
  publishing = true;
}

function setLatLong(latitude, longitude, target_altitude) {
  var i;
  var cur_latitude;
  var cur_longitude;
  var d;
  var altitude;

  if(target_altitude !== 0) {
    setAltitude(target_altitude, false, true);
  }

  for(i = 0; i < 3; i+=1) {
    console.log(`Going to (${latitude}, ${longitude}) from
                 (${getLatitude()}, ${getLongitude()}`);
    exit_on_fail(
      setTargetLatLong(latitude, longitude),
      `Failed to go to (${latitude}, ${longitude})`
    );
    sleep(500);
  }
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

  if(target_altitude !== 0) {
    goToAltitude(target_altitude, true, false);
  }
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

  var cmd_res;
  var altitude;

  var LANDING_ALTITUDE = 150;
  var INITIAL_ALTITUDE = 210;
  var HIGH_ALTITUDE = 230;
  var LAT1 = 45.83055;
  var LON1 = 13.95279;
  var LAT2 = 45.82889;
  var LON2 = 13.95086;

  if(DEMO) {
    LANDING_ALTITUDE = 105;
    INITIAL_ALTITUDE = 100;
    HIGH_ALTITUDE = 170;
    LAT1 = 45.91044;
    LON1 = 13.59627;
    LAT2 = 45.90733;
    LON2 = 13.59704;
  }
  publish();

  console.log("Will connect to", URL);

  console.log("[DEMO] Connecting...\n");
  connect();
  if(SIMULATION) {
    exit_on_fail(arm(), "Failed to arm");
    takeOffAndWait();
    goToAltitude(INITIAL_ALTITUDE + 1, true, true);

    LAT1 = (getInitialLatitude() - 0.00166).toFixed(5);
    LON1 = (getInitialLongitude() - 0.00193).toFixed(5);
    LAT2 = (LAT1 - 0.00166).toFixed(5);
    LON2 = (LON1 - 0.00193).toFixed(5);
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

  console.log("[DEMO] Going to first point...\n");
  setLatLong(LAT1, LON1, HIGH_ALTITUDE);

  sleep(30000);
  console.log("[DEMO] Going to landing coords...\n");
  setLatLong(LAT2, LON2, 0);
  console.log("[DEMO] Setting altitude...\n");
  goToAltitude(LANDING_ALTITUDE, true, true);

  console.log("[DEMO] Landing...\n");
  land();

  while(!landed()) {
    sleep(1000);
  }
  stop();
  stopPubsub();
})();
