/*jslint indent2 */
/*global console */
import {
  getAltitude,
  getInitialAltitude,
  landed,
  loiter,
  setTargetCoordinates
} from "{{ qjs_wrapper }}"; //jslint-quiet
import {sleep} from "os";
import {
  connect,
  goToAltitude,
  quit,
  startPubsub,
  takeOff,
  ALTITUDE_DIFF,
  IS_LEADER,
  LEADER_ID,
  SIMULATION
} from "{{ common }}"; //jslint-quiet

const FLIGH_ALTITUDE = 100;
const PARACHUTE_ALTITUDE = 35;

let INITIAL_ALTITUDE;
let START_ALTITUDE;

var leaderAltitudeAbs;
var leaderAltitudeRel;
var leaderLatitude;
var leaderLongitude;

function followLeader(leaderId, initialAltitude, altitudeDiff) {
  goToAltitude(START_ALTITUDE + ALTITUDE_DIFF, false, true);

  while(droneDict[leaderId].altitudeAbs == 0) {
    console.log("[DEMO] Waiting for leader to send its altitude");
    sleep(1000);
  }

  while(droneDict[leaderId].altitudeAbs < initialAltitude) {
    console.log(`[DEMO] Waiting for leader to reach altitude ${initialAltitude} (currently ${droneDict[leaderId].altitudeAbs})`);
    sleep(1000);
  }

  console.log("[DEMO] Switching to following mode...\n");
  do {
    leaderAltitudeAbs = droneDict[leaderId].altitudeAbs;
    leaderAltitudeRel = droneDict[leaderId].altitudeRel;
    leaderLatitude = droneDict[leaderId].latitude;
    leaderLongitude = droneDict[leaderId].longitude;

    setTargetCoordinates(
      leaderLatitude,
      leaderLongitude,
      leaderAltitudeAbs + altitudeDiff,
      0
    );
    sleep(500);
  } while(leaderAltitudeRel > PARACHUTE_ALTITUDE);

  console.log("[DEMO] Stop following...\n");
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

const droneDict = startPubsub();

console.log("[DEMO] Connecting...\n");
connect();

while(getInitialAltitude() == 0) {
  console.log("[DEMO] Waiting for first telemetry\n");
  sleep(1000);
}

INITIAL_ALTITUDE = getInitialAltitude();
START_ALTITUDE = INITIAL_ALTITUDE + FLIGH_ALTITUDE;

if(SIMULATION) {
  takeOff(START_ALTITUDE + 1);
}

waitForAltitude(START_ALTITUDE);

console.log("[DEMO] Setting loiter mode...\n");
loiter();
sleep(3000);

if(!IS_LEADER) {
  followLeader(LEADER_ID, START_ALTITUDE, ALTITUDE_DIFF);
}

console.log("[DEMO] Loitering until manual intructions are given\n")

waitForLanding();
quit();
