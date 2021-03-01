#include <chrono>
#include <cmath>
#include <cstdint>
#include <mavsdk/mavsdk.h>
#include <mavsdk/plugins/action/action.h>
#include <mavsdk/plugins/mavlink_passthrough/mavlink_passthrough.h>
#include <mavsdk/plugins/telemetry/telemetry.h>
#include <iostream>
#include <fstream>
#include <functional>
#include <future>
#include <memory>
#include <thread>

#include "mavsdk_wrapper.h"

using namespace mavsdk;
using std::chrono::seconds;
using std::this_thread::sleep_for;

#define ERROR_CONSOLE_TEXT "\033[31m" // Turn text on console red
#define TELEMETRY_CONSOLE_TEXT "\033[34m" // Turn text on console blue
#define NORMAL_CONSOLE_TEXT "\033[0m" // Restore normal console colour

static std::ofstream log_file_fd;

static Mavsdk _mavsdk;
static Telemetry * telemetry;
static Action * action;
static MavlinkPassthrough * mavlink_passthrough;
static std::shared_ptr<System> msystem;

static auto prom = std::promise<std::shared_ptr<System>>{};
static std::future<std::shared_ptr<System>> fut;

static double drone_la;
static double drone_lo;
static double drone_roll;
static double drone_pitch;
static double drone_yaw;
static float drone_a;
static float drone_at;
static Telemetry::FlightMode flight_mode;

static double initial_drone_la;
static double initial_drone_lo;
static double initial_drone_la_rad;
static double initial_drone_lo_rad;
static float initial_drone_a;
static double xy_ratio;
static bool initial_coords_set = false;

static const double PI = 3.14159265358979323846264338328F;
static const double EARTH_RADIUS = 6371000.F;

static int mavsdk_started = 0;
static void (*publish_fn)(double, double, float);

// Logs functions

static void log(std::string message) {
    log_file_fd << message << std::endl;
}

static void log_error(std::string message) {
    log(ERROR_CONSOLE_TEXT + message + NORMAL_CONSOLE_TEXT);
}

template <class Enumeration>
static void log_error_from_result(std::string message, Enumeration result) {
  std::ostringstream oss;
  oss << message << ": " << result;
  log_error(oss.str());
}

static void log_telemetry(std::string message) {
          // set to blue                 set to default color again
    log(TELEMETRY_CONSOLE_TEXT + message + NORMAL_CONSOLE_TEXT);
}

// Action functions

static int doAction(Action::Result (Action::*toDo)(void) const, std::string failure_message) {
    if(!mavsdk_started) {
        log_error("Mavsdk not started");
        return -1;
    }

    const Action::Result result = (action->*toDo)();
    if(result != Action::Result::Success) {
        log_error_from_result(failure_message, result);
        return -1;
    }
    return 0;
}

static int doMavlinkCommand(MavlinkPassthrough::CommandLong command, std::string failure_message) {
    const MavlinkPassthrough::Result result = mavlink_passthrough->send_command_long(command);
    if(result != MavlinkPassthrough::Result::Success) {
        log_error_from_result(failure_message, result);
        return -1;
    }
    return 0;
}

// Connexion management functions

int start(const char * url, const char * log_file, int timeout,
          void (*publishCoordinates)(double, double, float))
{
    std::string connection_url(url);
    ConnectionResult connection_result;
    log_file_fd.open(log_file);

    connection_result = _mavsdk.add_any_connection(connection_url);
    if (connection_result != ConnectionResult::Success) {
        log_error_from_result("Connection failed", connection_result);
        return -1;
    }

    log("Waiting to discover msystem...");
    fut = prom.get_future();

    _mavsdk.subscribe_on_new_system([]() {
        auto msystem_tmp = _mavsdk.systems().back();

        if (msystem_tmp->has_autopilot()) {
            log("Discovered autopilot");

            // Unsubscribe again as we only want to find one system.
            _mavsdk.subscribe_on_new_system(nullptr);
            prom.set_value(msystem_tmp);
        }
    });

    if (fut.wait_for(seconds(timeout)) == std::future_status::timeout) {
        log_error("No autopilot found, exiting.");
        return -1;
    }

    msystem = fut.get();
    telemetry = new Telemetry(msystem);
    action = new Action(msystem);
    mavlink_passthrough = new MavlinkPassthrough(msystem);

    log("Subscribing to flight mode...");
    // Subscribe to receive updates on flight mode. You can find out whether FollowMe is active.
    telemetry->subscribe_flight_mode([](Telemetry::FlightMode _flight_mode) {
        if(flight_mode != _flight_mode) {
            flight_mode = _flight_mode;
        }
    });

    /*log("Subscribing to Euler angle...");
    telemetry->subscribe_attitude_euler([](Telemetry::EulerAngle euler_angle) {
        drone_roll = euler_angle.roll_deg;
        drone_pitch = euler_angle.pitch_deg;
        drone_yaw = euler_angle.yaw_deg;
    });*/

    log("Subscribing to position...");
    // Set up callback to monitor altitude while the vehicle is in flight
    publish_fn = publishCoordinates;
    telemetry->subscribe_position([](Telemetry::Position position) {
        drone_la = position.latitude_deg;
        drone_lo = position.longitude_deg;
        drone_a = position.absolute_altitude_m;
        drone_at = position.relative_altitude_m;
        publish_fn(drone_la, drone_lo, drone_a);

        if(!initial_coords_set && drone_la != 0) {
            initial_drone_la = drone_la;
            initial_drone_lo = drone_lo;
            initial_drone_la_rad = (PI * drone_la) / 180.F;
            initial_drone_lo_rad = (PI * drone_lo) / 180.F;
            initial_drone_a = drone_a;
            xy_ratio = std::cos(initial_drone_la_rad);
            initial_coords_set = true;
        }

        std::ostringstream oss;
	      oss << drone_a << " m " << drone_at << " m "
            << drone_la << " " << drone_lo << " ";
        log_telemetry(oss.str());
    });
    log("MAVSDK started...");
    mavsdk_started = 1;
    return 0;
}

int stop() {
    if(!mavsdk_started)
        return -1;
    
    if(!landed()) {
      log_error("You must land first !");
      return -1;
    }

    if(doAction(&Action::shutdown, "Shutdown failed")) {
        return -1;
    }

    // Delete pointers
    delete action;
    delete mavlink_passthrough;
    delete telemetry;
    log_file_fd.close();

    return 0;
}

int reboot() {
    return doAction(&Action::reboot, "Rebooting failed");
}

// Flight state management functions

int arm(void) {
    if(!mavsdk_started)
        return -1;

    while(!telemetry->health().is_home_position_ok) {
        log("Waiting for home position to be set");
        sleep_for(seconds(1));
    }

    log("Arming...");
    return doAction(&Action::arm, "Arming failed");
}

int doParachute(int param) {
    if(!mavsdk_started)
        return -1;

    MavlinkPassthrough::CommandLong command;
    command.command = MAV_CMD_DO_PARACHUTE;
    command.param1 = param; //see https://mavlink.io/en/messages/common.html#PARACHUTE_ACTION
    command.target_sysid = mavlink_passthrough->get_target_sysid();
    command.target_compid = mavlink_passthrough->get_target_compid();
    return doMavlinkCommand(command, "Parachute failed");
}

int land(void)
{
    log("Landing...");
    if(doAction(&Action::terminate, "Land failed")) {
        return -1;
    }

    // Check if vehicle is still in air
    while (telemetry->in_air()) {
        log("Vehicle is landing...");
        sleep_for(seconds(1));
    }
    log("Landed!");

    // We are relying on auto-disarming but let's keep watching the telemetry for a bit longer.
    sleep_for(seconds(10));
    log("Finished...");

    return 0;
}

int loiter(double radius) {
    if(!mavsdk_started)
        return -1;

    if(flight_mode == Telemetry::FlightMode::Hold) {
	      std::cout << "Flight mode is " << flight_mode << std::endl;
	      return 0;
    }
    return loiterUnlimited(radius, drone_la, drone_lo, drone_a);
}

int takeOff(void)
{
    if(doAction(&Action::takeoff, "Takeoff failed")) {
        return -1;
    }

    while(flight_mode != Telemetry::FlightMode::Takeoff) {
        sleep_for(seconds(1));
    }

    log("Taking off...");
    return 0;
}

int takeOffAndWait(void) {
    if(takeOff()) {
        return -1;
    }

    while(flight_mode == Telemetry::FlightMode::Takeoff) {
        sleep_for(seconds(1));
    }
    return 0;
}

// Flight management functions

int doReposition(double la, double lo, double a, double y) {
    if(!mavsdk_started)
        return -1;

    MavlinkPassthrough::CommandLong command;
    command.command = MAV_CMD_DO_REPOSITION;
    command.param1 = -1; // Ground speed, -1 for default
    command.param2 = 1; // Bitmask of option flags (https://mavlink.io/en/messages/common.html#MAV_DO_REPOSITION_FLAGS)
    command.param4 = y; // loiter direction, 0: clockwise 1: counter clockwise
    command.param5 = la;
    command.param6 = lo;
    command.param7 = a;
    command.target_sysid = mavlink_passthrough->get_target_sysid();
    command.target_compid = mavlink_passthrough->get_target_compid();

    return doMavlinkCommand(command, "Reposition failed");
}

int loiterUnlimited(double radius, double la, double lo, double a) {
    if(!mavsdk_started)
        return -1;

    MavlinkPassthrough::CommandLong command;
    command.command = MAV_CMD_NAV_LOITER_UNLIM;
    command.param2 = radius; // Loiter radius around waypoint. If positive loiter clockwise, else counter-clockwise
    command.param5 = la;
    command.param6 = lo;
    command.param7 = a;
    command.target_sysid = mavlink_passthrough->get_target_sysid();
    command.target_compid = mavlink_passthrough->get_target_compid();

    return doMavlinkCommand(command, "Loiter failed");
}

int setAirspeed(double airspeed) {
    if(!mavsdk_started)
        return -1;

    MavlinkPassthrough::CommandLong command;
    command.command = 40000;
    command.param1 = 1 | 2 | 4 | 8;
    command.param2 = 2 | 4 | 8;
    command.param3 = (float) airspeed;
    command.target_sysid = mavlink_passthrough->get_target_sysid();
    command.target_compid = mavlink_passthrough->get_target_compid();

    return doMavlinkCommand(command, "Setting airspeed failed");
}

int setAltitude(double altitude) {
    if(!mavsdk_started)
        return -1;

    MavlinkPassthrough::CommandLong command;
    command.command = 40000;
    command.param1 = 1 | 2 | 4 | 8;
    command.param2 = 1 | 2 | 8;
    command.param3 = (float) altitude;
    command.target_sysid = mavlink_passthrough->get_target_sysid();
    command.target_compid = mavlink_passthrough->get_target_compid();

    return doMavlinkCommand(command, "Setting altitude failed");
}

int setTargetAltitude(double a)
{
    if(!mavsdk_started)
        return -1;

    log("Going to altitude " + std::to_string(a) + "m");
    const Action::Result result = action->goto_location(drone_la, drone_lo, (float) a, 0);
    if (result != Action::Result::Success) {
        log_error_from_result("Goto location failed", result);
        return -1;
    }
    return 0;
}

int setTargetCoordinates(double la, double lo, double a, double y)
{
    if(!mavsdk_started)
        return -1;

    std::cout << "Going to location (" << la << " , " << lo << ") "
              << a <<  " m " << std::endl;
    const Action::Result result = action->goto_location(la, lo, (float) a, (float) y);
    if (result != Action::Result::Success) {
        log_error_from_result("Goto location failed", result);
        return -1;
    }
    return 0;
}

int setTargetCoordinatesXYZ(double x, double y, double z) {
    double la, lo;

    la = ((initial_drone_la_rad + y / EARTH_RADIUS) * 180.F) / PI;
    lo = ((initial_drone_lo_rad + x / (EARTH_RADIUS * xy_ratio)) * 180.F) / PI;

    return setTargetCoordinates(la, lo, z, 0);
}

int setTargetLatLong(double la, double lo) {
    return setTargetCoordinates(la, lo, drone_a, 0);
}

// Information functions

double getAltitude(void) {
    return drone_a;
}

double getInitialAltitude(void) {
    return initial_drone_a;
}

double getInitialLatitude(void) {
    return initial_drone_la;
}

double getInitialLongitude(void) {
    return initial_drone_lo;
}

double getLatitude(void) {
    return drone_la;
}

double getLongitude(void) {
    return drone_lo;
}

double getPitch(void) {
    return drone_pitch;
}

double getRoll(void) {
    return drone_roll;
}

double getTakeOffAltitude(void) {
    const std::pair<Action::Result, float> response = action->get_takeoff_altitude();

    if(response.first != Action::Result::Success) {
        log_error_from_result("Get takeoff altitude failed", response.first);
        return -1;
    }
    return response.second;
}

double getYaw(void) {
    return drone_yaw;
}

int healthAllOk(void)
{
    return telemetry->health_all_ok();
}

int landed(void) {
  return !telemetry->in_air();
}
