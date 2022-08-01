import {
  arm,
  doParachute,
  getAltitude,
  getAltitudeRel,
  getInitialAltitude,
  getLatitude,
  getLongitude,
  getYaw,
  initPubsub,
  landed,
  loiter,
  reboot,
  setAirspeed,
  setAltitude,
  setCheckpoint,
  setTargetCoordinates,
  start,
  stop,
  stopPubsub,
  takeOffAndWait,
  Drone
} from "{{ qjs_wrapper }}";
import {sleep, Worker} from "os";
import * as std from "std";

const IP = "{{ autopilot_ip }}";
const URL = "udp://" + IP + ":7909";
const LOG_FILE = "{{ log_dir }}/mavsdk-log";

const IS_LEADER = {{ 'true' if is_leader else 'false' }};
const LEADER_ID = {{ leader_id }};
const IS_PUBLISHER = {{ 'true' if is_publisher else 'false' }}
const SIMULATION = {{ 'true' if is_a_simulation else 'false' }};

const droneIdList = [{{ drone_id_list | join(', ') }}];
const droneDict = {};

const pubsubScript = "{{ pubsub_script }}";
var pubsubWorker;
var pubsubRunning = false;

const me = {
  'id': "{{ id }}",
  'getCurrentPosition': function() {
    return {
      'x': getLatitude(),
      'y': getLongitude(),
      'z': getAltitudeRel()
    };
  },
  'onStart': function() {},
  'onUpdate': function() {},
  'setAirspeed': setAirspeed,
  'setTargetCoordinates': setTargetCoordinates
}

function connect() {
  console.log("Will connect to", URL);
  exit_on_fail(start(URL, LOG_FILE, 60), "Failed to connect to " + URL);
}

function exit_on_fail(ret, msg) {
  if(ret) {
    console.log(msg);
    quit();
    std.exit(-1);
  }
}

function quit() {
  stop();
  if(pubsubRunning) {
    stopPubsub();
  }
}

function takeOff() {
  exit_on_fail(arm(), "Failed to arm");
  takeOffAndWait();
}

function waitForLanding() {
  while(!landed()) {
    sleep(1000);
  }
}

if(IS_PUBLISHER) {
  console.log("Connecting to aupilot\n");
  connect();
}

pubsubWorker = new Worker(pubsubScript);
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

pubsubWorker.postMessage({ action: "run", id: me.id, publish: IS_PUBLISHER });
pubsubRunning = true;

{{ flight_script }}

if(IS_PUBLISHER && SIMULATION) {
  takeOff();
}

me.onStart()
me.onUpdate();

if(IS_PUBLISHER) {
  waitForLanding();
  quit();
} else {
  stopPubsub();
};
