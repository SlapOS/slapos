import * as mavsdk from "{{ mavsdk }}";
import { publish } from "{{ open62541 }}";
import * as os from "os";
import * as std from "std";

function exit_on_fail(ret, msg) {
  if(ret) {
    console.log(msg);
    std.exit(-1);
  }
}

const IP    = "169.79.1.1";
const PORT  = "7909";
const LOG_FILE  = "{{ log_dir }}/mavsdk-log";
const EPSILON = 105;
const EPSILON_YAW = 6;
const EPSILON_ALTITUDE = 2;
const TARGET_YAW = 0;

const DEMO = false;

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

const URL = "udp://" + IP + ":" + PORT;

std.printf("Will connect to %s\n", URL);

function connect() {
  exit_on_fail(mavsdk.start(URL, LOG_FILE, 60), "Failed to connect to " + URL);
}

function abs(x) {
  if(x > 0)
    return x
  return -x;
}
function distance(lat1, lon1, lat2, lon2) {
  var R = 6371e3; // meters
  var la1 = lat1 * Math.PI/180; // la, lo in radians
  var la2 = lat2 * Math.PI/180;
  var diffla = (lat2-lat1) * Math.PI/180;
  var difflo = (lon2-lon1) * Math.PI/180;

  var a = Math.sin(diffla/2) * Math.sin(diffla/2) +
            Math.cos(la1) * Math.cos(la2) *
            Math.sin(difflo/2) * Math.sin(difflo/2);
  var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));

  var d = R * c; // in meters
  return d;
}

function setLatLong(latitude, longitude, target_altitude) {
  if(target_altitude != 0)
    setAltitude(target_altitude, false, true);

  var i;
  for(i = 0; i < 3; i++) {
    exit_on_fail(mavsdk.setTargetLatLong(latitude, longitude), "Failed to go to (" + latitude + ", " + longitude + ")");
    os.sleep(500);
  }
  while(true) {
    var cur_latitude = mavsdk.getLatitude();
    var cur_longitude = mavsdk.getLongitude();
    var d = distance(cur_latitude, cur_longitude, latitude, longitude);
    std.printf("Waiting for drone to get to destination (%s m), (%s , %s), (%s, %s)\n", d, cur_latitude, cur_longitude, latitude, longitude);
    if(d < EPSILON) {
      os.sleep(6000);
      return;
    }
    os.sleep(1000);
  }

  if(target_altitude != 0)
    setAltitude(target_altitude, true, false);
}

function setAltitude(target_altitude, wait, go) {
  if(go)
    exit_on_fail(mavsdk.setAltitude(target_altitude), "Failed to go to altitude " + target_altitude + " m ");

  if(wait) {
    while(true) {
      var altitude = mavsdk.getAltitude();
      std.printf("[DEMO] Waiting for altitude... (%s , %s)\n", altitude, target_altitude);
      if(abs(altitude - target_altitude) < EPSILON_ALTITUDE)
        break;
      os.sleep(1000);
    }
  }
}

function land() {
  var latitude, longitude;

  console.log("[DEMO] Going to landing coords...\n");
  setLatLong(LAT2, LON2, 0);
  console.log("[DEMO] Setting altitude...\n");
  setAltitude(LANDING_ALTITUDE, true, true);

  while(true) {
    var yaw = mavsdk.getYaw();
    std.printf("[DEMO] Waiting for yaw... (%s , %s)\n", yaw, TARGET_YAW);
    if(abs(yaw - TARGET_YAW) < EPSILON_YAW)
      break;
    os.sleep(250);
  }

  std.printf("[DEMO] Deploying parachute...\n");
  exit_on_fail(mavsdk.doParachute(2), "Failed to deploy parachute");
}

console.log("[DEMO] Connecting...\n");
connect();
console.log("[DEMO] Setting loiter mode...\n");

while(true) {
  var altitude = mavsdk.getAltitude();
  std.printf("[DEMO] Waiting for altitude... (%s , %s)\n", altitude, INITIAL_ALTITUDE);
  if(altitude > INITIAL_ALTITUDE)
    break;
  os.sleep(1000);
}

mavsdk.loiter();
os.sleep(1000);

console.log("[DEMO] Going to first point...\n");
setLatLong(LAT1, LON1, HIGH_ALTITUDE);

os.sleep(30000);
console.log("[DEMO] Landing...\n");
land();