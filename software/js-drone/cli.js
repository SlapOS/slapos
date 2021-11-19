/*jslint indent2 */
/*global console, std */

import {
  arm,
  doParachute,
  land,
  loiter,
  setAirspeed,
  setAltitude,
  setTargetLatLong,
  start,
  stop,
  stopPubsub,
  reboot,
  takeOff
} from "{{ qjs_wrapper }}"; //jslint-quiet
import {sleep, Worker} from "os";
/*jslint-disable*/
import * as std from "std";
/*jslint-enable*/

const IP = "{{ autopilot_ip }}";
const PORT = "7909";
const URL = "udp://" + IP + ":" + PORT;
const LOG_FILE = "{{ log_dir }}/mavsdk-log";

var publishing = false;
var worker;

function disconnect() {
  stop();
  return 0;
}

function displayMessage(message) {
  console.log(message);
  return 0;
}

function parachute(param) {
  doParachute(param);
  return 0;
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

const wrongParameters = displayMessage.bind(null, "Wrong parameters");

function checkNumber(value, toExecute) {
  return (
    Number.isNaN(value)
    ? wrongParameters
    : toExecute.bind(null, value)
  );
}

function cli() {
  let s;
  let undefined_cmd;
  let altitude;
  let cmd;
  let timeout;
  let name;
  let latitude;
  let longitude;
  let param;
  let speed;

  const help = `
    connect(timeout)
    disconnect
    arm
    takeoff
    land
    parachute(action)
    goto(point)
    altitude(altitude)
    speed(speed)
    stop
    gotoCoord(latitude, longitude)
    reboot
    exit
    help
 `;

  const f = std.fdopen(std.in, "r");
  let dict = {};

  console.log("Will connect to", URL);

  while (true) {
    std.printf("> ");
    s = f.getline();
    undefined_cmd = false;

    switch (s) {
    case "altitude":
      std.printf("Altitude: ");
      altitude = parseFloat(f.getline());
      cmd = checkNumber(altitude, setAltitude);
      break;

    case "arm":
      cmd = arm;
      break;

    case "connect":
      std.printf("Timeout: ");
      timeout = parseInt(f.getline());
      cmd = checkNumber(timeout, start.bind(null, URL, LOG_FILE));
      publish();
      break;

    case "define":
      std.printf("Name: ");
      name = f.getline();
      std.printf("Latitude: ");
      latitude = parseFloat(f.getline());
      std.printf("Longitude: ");
      longitude = parseFloat(f.getline());
      dict[name] = [latitude, longitude];
      cmd = displayMessage.bind(
        null,
        `${name} defined as ${latitude} ${longitude}`
      );
      break;

    case "disconnect":
      cmd = disconnect;
      break;

    case "exit":
      stopPubsub();
      return;

    case "goto":
      std.printf("Name: ");
      name = f.getline();
      if (dict.hasOwnProperty(name)) {
        latitude = dict[name][0];
        longitude = dict[name][1];
        cmd = checkNumber(longitude, checkNumber(latitude, setTargetLatLong));
      } else {
        cmd = displayMessage.bind(`${name} is not defined yet`);
      }
      break;

    case "gotoCoord":
      std.printf("Latitude: ");
      latitude = parseFloat(f.getline());
      std.printf("Longitude: ");
      longitude = parseFloat(f.getline());
      cmd = checkNumber(longitude, checkNumber(latitude, setTargetLatLong));
      break;

    case "help":
      cmd = displayMessage.bind(null, help);
      break;

    case "land":
      cmd = land;
      break;

    case "loiter":
      cmd = loiter;
      break;

    case "parachute":
      std.printf("Action: ");
      param = parseInt(f.getline());
      cmd = checkNumber(param, parachute);
      break;

    case "print":
      std.printf("Name: ");
      name = f.getline();
      displayMessage.bind(
        null,
        dict.hasOwnProperty(name)
        ? `${dict[name][0]}\n${dict[name][1]}`
        : `${name} undefined`
      );
      break;

    case "speed":
      std.printf("Speed: ");
      speed = parseFloat(f.getline());
      cmd = checkNumber(speed, setAirspeed);
      break;

    case "stop":
      cmd = stop;
      break;

    case "reboot":
      comd = reboot;
      break;

    case "takeoff":
      cmd = takeOff;
      break;

    default:
      undefined_cmd = true;
      cmd = displayMessage.bind(null, "    Undefined command");
    }

    let ret = cmd();
    if (ret !== 0) {
      console.log("    [ERROR] function:\n", cmd, "\nreturn value:", ret);
    } else if (s !== "help" && !undefined_cmd) {
      console.log("    Command successful");
    }
  }

  f.close();

  return;
}

cli();
