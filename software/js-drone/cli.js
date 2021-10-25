import * as mavsdk from "{{ mavsdk }}";
import * as os from "os";
import * as std from "std";

const LOG_FILE  = "{{ log_dir }}/mavsdk-log";

function test(a, b) {
  console.log(a, b);
}

function cli() {

        var f = std.fdopen(os.stdin, "r");

        std.printf("IP: ");
        const IP = f.getline();

        var dict = {};

        const URL = "udp://" + IP + ":7909";
        std.printf("Will connect to %s\n", URL);

        while(true) {
          std.printf("> ");
          var s = f.getline();
          var cmd;
          var undefined_cmd = false;

          switch(s) {
            case "connect":
              std.printf("Timeout: ");
              var timeout = parseInt(f.getline());
              if(isNaN(timeout)) {
                console.log("Wrong parameters");
                continue;
              }
              cmd = () => {return mavsdk.start(URL, LOG_FILE, timeout);};
              break;

            case "disconnect":
              cmd = () => {mavsdk.stop(); return 0;};
              break;

            case "arm":
              cmd = mavsdk.arm;
              break;

            case "takeoff":
              cmd = mavsdk.takeOff;
              break;

            case "land":
              cmd = mavsdk.land;
              break;

            case "define":
              std.printf("Name: ");
              var name = f.getline();
              std.printf("Latitude: ");
              var latitude = parseFloat(f.getline());
              std.printf("Longitude: ");
              var longitude = parseFloat(f.getline());
              dict[name] = [latitude, longitude];
              continue;

            case "print":
              std.printf("Name: ");
              var name = f.getline();
              if(name in dict) {
                console.log(dict[name][0]);
                console.log(dict[name][1]);
              }
              continue;

            case "parachute":
              std.printf("Action: ");
              var param = parseInt(f.getline());
              if(isNaN(param)) {
                console.log("Wrong parameters");
                continue;
              }

              cmd = () => {mavsdk.doParachute(param);return 0;};
              break;

            case "loiter":
              cmd = mavsdk.loiter;
              break;

            case "goto":
              std.printf("Name: ");
              var name = f.getline();
              if(name in dict) {
                var latitude = dict[name][0];
                var longitude = dict[name][1];
                if(isNaN(latitude) || isNaN(longitude)) {
                  console.log("Wrong parameters");
                  continue;
                }
                cmd = () => {return mavsdk.setTargetLatLong(latitude, longitude);};
              }
              else {
                std.printf("%s wasn't defined yet\n", name);
                continue;
              }
              break;

            case "altitude":
              std.printf("Altitude: ");
              var altitude = parseFloat(f.getline());
              if(isNaN(altitude)) {
                console.log("Wrong parameters");
                continue;
              }
              cmd = () => {return mavsdk.setAltitude(altitude);};
              break;
            case "speed":
              std.printf("Speed: ");
              var speed = parseFloat(f.getline());
              if(isNaN(speed)) {
                console.log("Wrong parameters");
                continue;
              }
              cmd = () => {return mavsdk.setAirspeed(speed);};
              break;

            case "gotoCoord":
              std.printf("Latitude: ");
              var latitude = parseFloat(f.getline());
              std.printf("Longitude: ");
              var longitude = parseFloat(f.getline());
              if(isNaN(latitude) || isNaN(longitude)) {
                console.log("Wrong parameters");
                continue;
              }
              cmd = () => {return mavsdk.setTargetLatLong(latitude, longitude);};
              break;

            case "exit":
              return;

            case "help":
              var help = `
              connect(timeout)
              disconnect
              arm
              takeoff
              land
              parachute(action)
              goto(point)
              altitude(altitude)
              speed(altitude)
              gotoCoord(latitude, longitude)
              exit
              help
              `;
              console.log(help);
              cmd = () => {return 0;};
              break;

            case "":
              continue;

            default:
              undefined_cmd = true;
              console.log("    Undefined command");
              cmd = () => {return 0;};
          }

          var ret = cmd();
          if( ret != 0 )
            console.log("    [ERROR] function:\n", cmd, "\nreturn value:", ret);
          else if (s != "help" && !undefined_cmd )
            console.log("    Command successful");
        }

        f.close();

	return;
}

cli();