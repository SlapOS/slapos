import * as mavsdk from "{{ qjs_wrapper }}";
import * as os from "os";
import { fdopen, printf } from "std";

const IP = "{{ autopilot_ip }}";
const PORT = "7909";
const URL = "udp://" + IP + ":" +  PORT;
const LOG_FILE  = "{{ log_dir }}/mavsdk-log";

function test(a, b) {
  console.log(a, b);
}

function cli() {

        var f = fdopen(os.stdin, "r");
        var dict = {};

        printf("Will connect to %s\n", URL);

        while(true) {
          printf("> ");
          var s = f.getline();
          var cmd;
          var undefined_cmd = false;

          switch(s) {
            case "connect":
              printf("Timeout: ");
              var timeout = parseInt(f.getline());
              if(isNaN(timeout)) {
                console.log("Wrong parameters");
                continue;
              }
              cmd = () => {return mavsdk.start(URL, LOG_FILE, timeout);};
	      var worker = new os.Worker("{{ publish_script }}");
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
              printf("Name: ");
              var name = f.getline();
              printf("Latitude: ");
              var latitude = parseFloat(f.getline());
              printf("Longitude: ");
              var longitude = parseFloat(f.getline());
              dict[name] = [latitude, longitude];
              continue;

            case "print":
              printf("Name: ");
              var name = f.getline();
              if(name in dict) {
                console.log(dict[name][0]);
                console.log(dict[name][1]);
              }
              continue;

            case "parachute":
              printf("Action: ");
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
              printf("Name: ");
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
                printf("%s wasn't defined yet\n", name);
                continue;
              }
              break;

            case "altitude":
              printf("Altitude: ");
              var altitude = parseFloat(f.getline());
              if(isNaN(altitude)) {
                console.log("Wrong parameters");
                continue;
              }
              cmd = () => {return mavsdk.setAltitude(altitude);};
              break;
            case "speed":
              printf("Speed: ");
              var speed = parseFloat(f.getline());
              if(isNaN(speed)) {
                console.log("Wrong parameters");
                continue;
              }
              cmd = () => {return mavsdk.setAirspeed(speed);};
              break;

            case "gotoCoord":
              printf("Latitude: ");
              var latitude = parseFloat(f.getline());
              printf("Longitude: ");
              var longitude = parseFloat(f.getline());
              if(isNaN(latitude) || isNaN(longitude)) {
                console.log("Wrong parameters");
                continue;
              }
              cmd = () => {return mavsdk.setTargetLatLong(latitude, longitude);};
              break;

            case "exit":
	      mavsdk.stopPubsub();
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
              speed(speed)
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
