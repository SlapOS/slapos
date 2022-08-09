{% set comma_separated_drone_id_list = ', '.join(drone_id_list.split()) -%}

/*global console*/
import {
  Drone,
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
  setAirspeed,
  setAltitude,
  setCheckpoint,
  setTargetCoordinates
} from "{{ qjs_wrapper }}";
import { Worker } from "os"
import * as std from "std";

(function (console, Worker) {
  // Every script is evaluated per drone
  "use strict";
  const drone_dict = {},
    drone_id_list = [{{ comma_separated_drone_id_list }}];

  var parent = Worker.parent,
    user_me = {
      //for debugging purpose
      fdopen: std.fdopen,
      in: std.in,
      //to move into user script
      setCheckpoint: setCheckpoint,
      //required to fly
      doParachute: doParachute,
      drone_dict: {},
      exit: function(exit_code) {
        parent.postMessage({type: "exited", exit: exit_code});
        parent.onmessage = null;
      },
      getAltitudeAbs: getAltitude,
      getCurrentPosition: function() {
        return {
          x: getLatitude(),
          y: getLongitude(),
          z: getAltitudeRel()
        };
      },
      getInitialAltitude: getInitialAltitude,
      getYaw: getYaw,
      id: {{ id }},
      landed: landed,
      loiter: loiter,
      setAirspeed: setAirspeed,
      setAltitude: setAltitude,
      setTargetCoordinates: setTargetCoordinates
    };

  function loadUserScript(path) {
    var script_content = std.loadFile(path);
    if (script_content === null) {
      console.log('Failed to load user script ' + path);
      std.exit(1);
    }
    try {
      std.evalScript(
        'function execUserScript(from, me) {' +
          script_content +
        '};'
      );
    } catch (e) {
      console.log('Failed to evaluate user script', e);
      std.exit(1);
    }
    execUserScript(null, user_me);

    // Call the drone onStart function
    if (user_me.hasOwnProperty('onStart')) {
      user_me.onStart();
    }
  }

  function handleMainMessage(evt) {
    var type = evt.data.type;

    if (type === 'initPubsub') {
      initPubsub(drone_id_list.length);
      for (let i = 0; i < drone_id_list.length; i++) {
        let id = drone_id_list[i];
        user_me.drone_dict[id] = new Drone(id);
        user_me.drone_dict[id].init(i);
      }
      parent.postMessage({type: "initialized"});
    }
    else if (type === 'load') {
      loadUserScript(evt.data.path);
      parent.postMessage({type: "loaded"});
    } else if (type === 'update') {
      // Call the drone onStart function
      if (user_me.hasOwnProperty('onUpdate')) {
        user_me.onUpdate(evt.data.timestamp);
      }
      parent.postMessage({type: "updated"});
    } else {
      throw new Error('Unsupported message type', type);
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

}(console, Worker));
