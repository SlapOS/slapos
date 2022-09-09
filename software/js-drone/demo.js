/*jslint indent2 */
/*global console */
import {
  getAltitude,
  getAltitudeRel,
  getInitialAltitude,
  getLatitude,
  getLongitude,
  landed,
  loiter,
  setCheckpoint,
  setTargetCoordinates
} from "{{ qjs_wrapper }}"; //jslint-quiet
import {sleep} from "os";
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
  IS_LEADER,
  LEADER_ID,
  SIMULATION
} from "{{ common }}"; //jslint-quiet

const FLIGH_ALTITUDE = 100;
const PARACHUTE_ALTITUDE = 35;

const checkpointList = [
  {
    "latitude": 45.64492790560583,
    "longitude": 14.25334942966329,
    "altitude": 585.1806861589965
  },
  {
    "latitude": 45.64316335436476,
    "longitude": 14.26332880184475,
    "altitude": 589.8802607573035
  },
  {
    "latitude": 45.64911917196595,
    "longitude": 14.26214792790128,
    "altitude": 608.6648153348965
  },
  {
    "latitude": 45.64122685351364,
    "longitude": 14.26590493128597,
    "altitude": 606.1448368129072
  },
  {
    "latitude": 45.64543355564817,
    "longitude": 14.27242391207985,
    "altitude": 630.0829598206344
  },
  {
    "latitude": 45.6372792927328,
    "longitude": 14.27533492411138,
    "altitude": 616.1839898415284
  },
  {
    "latitude": 45.64061299543953,
    "longitude": 14.26161958465814,
    "altitude": 598.0603137354178
  },
  {
    "latitude": 45.64032340702919,
    "longitude": 14.2682896662383,
    "altitude": 607.1243119862851
  }
];

const landingPoint = [
  {
    "latitude": 45.6398451,
    "longitude": 14.2699217
  }
];

let INITIAL_ALTITUDE;
let START_ALTITUDE;

var nextCheckpoint = 0;

var distanceToLandingPoint = 100;

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
  nextCheckpoint = droneDict[leaderId].lastCheckpoint + 1;
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

console.log("[DEMO] Connecting...\n");
connect();

const droneDict = startPubsub();

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

for (let i = nextCheckpoint; i < checkpointList.length; i++) {
  console.log(`[DEMO] Going to Checkpoint ${i}\n`);
  setLatLong(checkpointList[i].latitude, checkpointList[i].longitude, checkpointList[i].altitude + FLIGH_ALTITUDE);
  console.log(`[DEMO] Reached Checkpoint ${i}\n`);
  setCheckpoint(i);
  sleep(30000);
}

console.log("[DEMO] Setting altitude...\n");
goToAltitude(getAltitude() - getAltitudeRel() + PARACHUTE_ALTITUDE, true, true);

if(!IS_LEADER) {
  setLatLong(
    checkpointList[checkpointList.length - 1].latitude,
    checkpointList[checkpointList.length - 1].longitude,
    0
  );
}

while(distanceToLandingPoint > 20) {
  console.log(`[DEMO] Waiting to reache landing point (current distance is ${distanceToLandingPoint})`);
  distanceToLandingPoint = distance(getLatitude(), getLongitude(), landingPoint.latitude, landingPoint.longitude);
}

console.log("[DEMO] Landing...\n");
land();

waitForLanding();
quit();
