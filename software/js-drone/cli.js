/*jslint indent2 */
/*global console, std */

import {
  getInitialAltitude,
  loiter,
  setAirspeed,
  setAltitude,
  reboot
} from "{{ qjs_wrapper }}"; //jslint-quiet
import {
  connect,
  displayDronePositions,
  goTo,
  land,
  quit,
  startPubsub,
  takeOff
} from "{{ common }}"; //jslint-quiet
/*jslint-disable*/
import * as std from "std";
/*jslint-enable*/

var running = false;
const wrongParameters = displayMessage.bind(null, "Wrong parameters");

function checkNumber(value, toExecute) {
  return (
    Number.isNaN(value)
    ? wrongParameters
    : toExecute.bind(null, value)
  );
}

function displayMessage(message) {
  console.log(message);
  return 0;
}

function exit() {
  running = false;
  quit();
  return 0;
}

function getInput() {
  let undefined_cmd;
  let altitude;
  let cmd;
  let latitude;
  let longitude;
  let s;
  let speed;
  
  const help = `
    connect
    takeoff
    land
    goto(point)
    gotoCoord(latitude, longitude)
    altitude(altitude)
    speed(speed)
    positions
    reboot
    exit
    help
  `;

  const f = std.fdopen(std.in, "r");
  running = true;
  while (running) {
    std.printf("> ");
    s = f.getline();
    undefined_cmd = false;
  
    switch (s) {
    case "altitude":
      std.printf("Altitude: ");
      altitude = parseFloat(f.getline());
      cmd = checkNumber(altitude, setAltitude);
      break;
  
    case "connect":
      cmd = connect;
      startPubsub();
      break;
  
    case "exit":
      cmd = exit;
      break;
  
/*    case "gotoCoord":
      std.printf("Latitude: ");
      latitude = parseFloat(f.getline());
      std.printf("Longitude: ");
      longitude = parseFloat(f.getline());
      cmd = checkNumber(longitude, checkNumber(latitude, setTargetLatLong));
      break;*/
  
    case "help":
      cmd = displayMessage.bind(null, help);
      break;
  
    case "land":
      cmd = land;
      break;
  
    case "loiter":
      cmd = loiter;
      break;
  
    case "positions":
      cmd = displayDronePositions;
      break;
  
    case "reboot":
      cmd = reboot;
      break;
  
    case "speed":
      std.printf("Speed: ");
      speed = parseFloat(f.getline());
      cmd = checkNumber(speed, setAirspeed);
      break;
  
    case "takeoff":
      cmd = takeOff.bind(null, getInitialAltitude() + 60);
      break;
  
    default:
      undefined_cmd = true;
      cmd = displayMessage.bind(null, "    Undefined command");
    }
  
    let ret = cmd();
    if (ret) {
      console.log("    [ERROR] function:\n", cmd, "\nreturn value:", ret);
    }
    else if (s !== "help" && !undefined_cmd) {
      console.log("    Command successful");
    }
  };

  f.close();
}

getInput();
