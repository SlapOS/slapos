/*jslint indent2 */
/*global console */
import {
  getAltitude,
  getInitialLatitude,
  getInitialLongitude,
  landed,
  loiter,
  setTargetCoordinates
} from "{{ qjs_wrapper }}"; //jslint-quiet
import {sleep, SIGINT, SIGTERM, signal} from "os";
import {
  connect,
  distance,
  goToAltitude,
  land,
  quit,
  setLatLong,
  startPubsub,
  takeOff,
  ALTITUDE_DIFF,
  EPSILON,
  IS_LEADER,
  LEADER_ID,
  SIMULATION
} from "{{ common }}"; //jslint-quiet

var leaderAltitude;
var leaderLatitude;
var leaderLongitude;

var LANDING_ALTITUDE = 145;
var INITIAL_ALTITUDE = 215;
var HIGH_ALTITUDE = 235;

var LAT1 = 45.83055;
var LON1 = 13.95279;
var checkpoint1 = false;

var LAT2 = 45.82889;
var LON2 = 13.95086;
var checkpoint2 = false;

function followLeader(leaderId, initialAltitude, altitudeDiff, lat1, lon1, lat2,
                      lon2, epsilon, landingAltitude) {
  while(droneDict[leaderId].altitude < initialAltitude - altitudeDiff) {
    sleep(1000);
    console.log("[DEMO] Waiting for leader altitude");
  }

  console.log("[DEMO] Switching to following mode...\n");
  do {
    leaderAltitude = droneDict[leaderId].altitude;
    leaderLatitude = droneDict[leaderId].latitude;
    leaderLongitude = droneDict[leaderId].longitude;

    setTargetCoordinates(
      leaderLatitude,
      leaderLongitude,
      leaderAltitude + altitudeDiff,
      0
    );

    if (!checkpoint1) {
      if (distance(leaderLatitude, leaderLongitude, lat1, lon1) < epsilon) {
        checkpoint1 = true;
      }
    } else if (!checkpoint2) {
      if (distance(leaderLatitude, leaderLongitude, lat2, lon2) < epsilon) {
        checkpoint2 = true;
      }
    }
  } while(droneDict[leaderId].altitude > landingAltitude);

  console.log("[DEMO] Stop following...\n");
}

function stopHandler(sign) {
  console.log("received ctrl-c");
  quit();
}

function waitForAltitude(altitude) {
  var curAltitude;
  do {
    sleep(1000);
    curAltitude = getAltitude();
    console.log(
      `[DEMO] Waiting for altitude... (${curAltitude} , ${altitude})`);
  }
  while(curAltitude < altitude);
}

function waitForLanding() {
  while(!landed()) {
    sleep(1000);
  }
}

signal(SIGINT, stopHandler);
signal(SIGTERM, stopHandler);

const droneDict = startPubsub();

console.log("[DEMO] Connecting...\n");
connect();

if(SIMULATION) {
  LANDING_ALTITUDE = 100;
  INITIAL_ALTITUDE = 105;

  if(!IS_LEADER) {
    INITIAL_ALTITUDE += ALTITUDE_DIFF;
  }

  takeOff(INITIAL_ALTITUDE + 1);

  LAT1 = (getInitialLatitude() - 0.0045).toFixed(5);
  LON1 = (getInitialLongitude() - 0.006).toFixed(5);
  LAT2 = (LAT1 - 0.0045).toFixed(5);
  LON2 = (LON1 - 0.006).toFixed(5);
}

waitForAltitude(INITIAL_ALTITUDE);

console.log("[DEMO] Setting loiter mode...\n");
loiter();
sleep(1000);

if(!IS_LEADER) {
  followLeader(LEADER_ID, INITIAL_ALTITUDE, ALTITUDE_DIFF, LAT1, LON1, LAT2,
               LON2, EPSILON, LANDING_ALTITUDE);
}

if (!checkpoint1) {
  console.log("[DEMO] Going to first point...\n");
  setLatLong(LAT1, LON1, HIGH_ALTITUDE);
  sleep(30000);
}

if (!checkpoint2) {
  console.log("[DEMO] Going to landing coords...\n");
  setLatLong(LAT2, LON2, 0);
  console.log("[DEMO] Setting altitude...\n");
  goToAltitude(LANDING_ALTITUDE, true, true);
}

if(!IS_LEADER) {
  setLatLong( (LAT2 - 0.001).toFixed(5), (LON2 - 0.001).toFixed(5), 0);
}

console.log("[DEMO] Landing...\n");
land();

waitForLanding();
quit();
