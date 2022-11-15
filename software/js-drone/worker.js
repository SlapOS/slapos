/*jslint nomen: true, indent: 2, maxerr: 3, maxlen: 80 */
/*global console, getAltitude, getAltitudeRel, getInitialAltitude, getLatitude,
  getLongitude, getYaw, execUserScript, initPubsub, isInManualMode, landed,
  loiter, setAirspeed, setAltitude, setManualControlInput, setMessage,
  setTargetCoordinates, std, triggerParachute, Drone, Worker*/
import {
  Drone,
  triggerParachute,
  getAltitude,
  getAltitudeRel,
  getInitialAltitude,
  getLatitude,
  getLongitude,
  getYaw,
  initPubsub,
  isInManualMode,
  landed,
  loiter,
  setAirspeed,
  setAltitude,
  setManualControlInput,
  setMessage,
  setTargetCoordinates
} from {{ json_module.dumps(qjs_wrapper) }};
import * as std from "std";
import { Worker } from "os";

(function (console, getAltitude, getAltitudeRel, getInitialAltitude,
           getLatitude, getLongitude, getYaw, initPubsub, isInManualMode,
           landed, loiter, setAirspeed, setAltitude, setManualControlInput,
           setMessage, setTargetCoordinates, std, triggerParachute, Drone,
           Worker) {
  // Every script is evaluated per drone
  "use strict";

  var CONF_PATH = {{ json_module.dumps(configuration) }},
    conf_file = std.open(CONF_PATH, "r"),
    configuration = JSON.parse(conf_file.readAsString()),
    parent = Worker.parent,
    user_me = {
      //for debugging purpose
      fdopen: std.fdopen,
      in: std.in,
      //required to fly
      triggerParachute: triggerParachute,
      drone_dict: {},
      exit: function (exit_code) {
        parent.postMessage({type: "exited", exit: exit_code});
        parent.onmessage = null;
      },
      getAltitudeAbs: getAltitude,
      getCurrentPosition: function () {
        return {
          x: getLatitude(),
          y: getLongitude(),
          z: getAltitudeRel()
        };
      },
      getInitialAltitude: getInitialAltitude,
      getYaw: getYaw,
      id: configuration.id,
      landed: landed,
      loiter: loiter,
      sendMsg: function (msg, id) {
        if (id === undefined) { id = -1; }
        setMessage(JSON.stringify({ content: msg, dest_id: id }));
      },
      setAirspeed: setAirspeed,
      setAltitude: setAltitude,
      setTargetCoordinates: setTargetCoordinates
    };
  conf_file.close();

  function loadUserScript(path) {
    var script_content = std.loadFile(path);
    if (script_content === null) {
      console.log("Failed to load user script " + path);
      std.exit(1);
    }
    try {
      std.evalScript(
        "function execUserScript(from, me) {" + script_content + "};"
      );
    } catch (e) {
      console.log("Failed to evaluate user script", e);
      std.exit(1);
    }
    execUserScript(null, user_me);

    // Call the drone onStart function
    if (user_me.hasOwnProperty("onStart")) {
      user_me.onStart();
    }
  }

  function handleMainMessage(evt) {
    var type = evt.data.type,
      message;

    if (type === "initPubsub") {
      initPubsub(configuration.droneIdList.length);
      configuration.droneIdList.forEach(function (drone_id, index) {
        drone_id = configuration.droneIdList[index];
        user_me.drone_dict[drone_id] = new Drone(drone_id);
        user_me.drone_dict[drone_id].init(index);
      });
      parent.postMessage({type: "initialized"});
    } else if (type === "load") {
      loadUserScript(evt.data.path);
      parent.postMessage({type: "loaded"});
    } else if (type === "update") {
      Object.entries(user_me.drone_dict).forEach(function ([id, drone]) {
        message = drone.message;
        if (user_me.id === Number(id) && message.length > 0) {
          message = JSON.parse(message);
          if (user_me.hasOwnProperty("onGetMsg") &&
              [-1, user_me.id].includes(message.dest_id)) {
            user_me.onGetMsg(message.content);
          }
        }
      });
      // Call the drone onStart function
      if (user_me.hasOwnProperty("onUpdate")) {
        if (configuration.isADrone && isInManualMode()) {
          setManualControlInput();
        }
        user_me.onUpdate(evt.data.timestamp);
      }
      parent.postMessage({type: "updated"});
    } else {
      throw new Error("Unsupported message type", type);
    }
  }

  parent.onmessage = function (evt) {
    try {
      handleMainMessage(evt);
    } catch (error) {
      // Catch all potential bug to exit the main process
      // if it occurs
      console.log(error);
      std.exit(1);
    }
  };
}(console, getAltitude, getAltitudeRel, getInitialAltitude, getLatitude,
  getLongitude, getYaw, initPubsub, isInManualMode, landed, loiter, setAirspeed,
  setAltitude, setManualControlInput, setMessage, setTargetCoordinates, std,
  triggerParachute, Drone, Worker));
