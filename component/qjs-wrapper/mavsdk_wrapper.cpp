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

int start(const char * url, const char * log_file, int timeout,
          void (*publishCoordinates)(double, double, float))
{
    std::string connection_url(url);
    ConnectionResult connection_result;
    log_file_fd.open(log_file);

    connection_result = _mavsdk.add_any_connection(connection_url);

    if (connection_result != ConnectionResult::Success) {
        log_file_fd << ERROR_CONSOLE_TEXT << "Connection failed: " << connection_result
                  << NORMAL_CONSOLE_TEXT << std::endl;
        return 1;
    }

    log_file_fd << "Waiting to discover msystem..." << std::endl;
    fut = prom.get_future();

    _mavsdk.subscribe_on_new_system([]() {
        auto msystem_tmp = _mavsdk.systems().back();

        if (msystem_tmp->has_autopilot()) {
            log_file_fd << "Discovered autopilot" << std::endl;

            // Unsubscribe again as we only want to find one system.
            _mavsdk.subscribe_on_new_system(nullptr);
            prom.set_value(msystem_tmp);
        }
    });

    if (fut.wait_for(seconds(timeout)) == std::future_status::timeout) {
        log_file_fd << ERROR_CONSOLE_TEXT << "No autopilot found, exiting." << NORMAL_CONSOLE_TEXT
                  << std::endl;
        return 1;
    }

    msystem = fut.get();
    telemetry = new Telemetry(msystem);
    action = new Action(msystem);
    mavlink_passthrough = new MavlinkPassthrough(msystem);

    log_file_fd << "Subscribing to flight mode..." << std::endl;
    // Subscribe to receive updates on flight mode. You can find out whether FollowMe is active.
    telemetry->subscribe_flight_mode([](Telemetry::FlightMode _flight_mode) {
            flight_mode = _flight_mode;
    });

    log_file_fd << "Subscribing to Euler angle..." << std::endl;
    telemetry->subscribe_attitude_euler([](Telemetry::EulerAngle euler_angle) {
        drone_roll = euler_angle.roll_deg;
        drone_pitch = euler_angle.pitch_deg;
        drone_yaw = euler_angle.yaw_deg;
    });

    log_file_fd << "Subscribing to position..." << std::endl;
    // Set up callback to monitor altitude while the vehicle is in flight
    publish_fn = publishCoordinates;
    telemetry->subscribe_position([](Telemetry::Position position) {
        drone_la = position.latitude_deg;
        drone_lo = position.longitude_deg;
        drone_a = position.absolute_altitude_m;
        drone_at = position.relative_altitude_m;
        publish_fn(drone_la, drone_lo, drone_a);

        if(!initial_coords_set) {
            initial_drone_la = drone_la;
            initial_drone_lo = drone_lo;
            initial_drone_la_rad = (PI * drone_la) / 180.F;
            initial_drone_lo_rad = (PI * drone_lo) / 180.F;
            initial_drone_a = drone_a;
            xy_ratio = std::cos(initial_drone_la_rad);
            initial_coords_set = true;
        }
        log_file_fd << TELEMETRY_CONSOLE_TEXT // set to blue
                  <<  drone_a << " m " << drone_at << " m " << drone_la << " " << drone_lo << " "
                  << NORMAL_CONSOLE_TEXT // set to default color again
                  << std::endl;
    });
    log_file_fd << "MAVSDK started..." << std::endl;
    mavsdk_started = 1;
    return 0;
}

int doParachute(int param) {
    if(!mavsdk_started)
        return 1;

    MavlinkPassthrough::CommandLong command;
    command.command = MAV_CMD_DO_PARACHUTE;
    command.param1 = param;
    command.target_sysid = mavlink_passthrough->get_target_sysid();
    command.target_compid = mavlink_passthrough->get_target_compid();

    return !(mavlink_passthrough->send_command_long(command) == MavlinkPassthrough::Result::Success);
}

int setAltitude(double altitude) {
    if(!mavsdk_started)
        return 1;

    MavlinkPassthrough::CommandLong command;
    command.command = 40000;
    command.param1 = 1 | 2 | 4 | 8;
    command.param2 = 1 | 2 | 8;
    command.param3 = (float) altitude;
    command.target_sysid = mavlink_passthrough->get_target_sysid();
    command.target_compid = mavlink_passthrough->get_target_compid();

    return !(mavlink_passthrough->send_command_long(command) == MavlinkPassthrough::Result::Success);
}

int setAirspeed(double airspeed) {
    if(!mavsdk_started)
        return 1;

    MavlinkPassthrough::CommandLong command;
    command.command = 40000;
    command.param1 = 1 | 2 | 4 | 8;
    command.param2 = 2 | 4 | 8;
    command.param3 = (float) airspeed;
    command.target_sysid = mavlink_passthrough->get_target_sysid();
    command.target_compid = mavlink_passthrough->get_target_compid();

    return !(mavlink_passthrough->send_command_long(command) == MavlinkPassthrough::Result::Success);
}

int loiter(void) {
    if(!mavsdk_started)
        return 1;

    if(flight_mode == Telemetry::FlightMode::Hold) {
      std::cout << "Flight mode is " << flight_mode << std::endl;
      return 0;
    }

    MavlinkPassthrough::CommandLong command;
    command.command = MAV_CMD_DO_REPOSITION;
    command.param1 = -1.f;
    command.param2 = 1.f;
    command.param3 = 0;
    command.param5 = drone_la;
    command.param6 = drone_lo;
    command.param7 = drone_a;
    command.target_sysid = mavlink_passthrough->get_target_sysid();
    command.target_compid = mavlink_passthrough->get_target_compid();

    const MavlinkPassthrough::Result cmd_result = mavlink_passthrough->send_command_long(command);
    if (cmd_result != MavlinkPassthrough::Result::Success) {
        log_file_fd << ERROR_CONSOLE_TEXT << "Loiter failed" << cmd_result
	       	          << NORMAL_CONSOLE_TEXT << std::endl;
       return 1;
   }

   log_file_fd << "Loiter mode set to ( " << drone_la << " , " << drone_lo
               << " ) " << drone_a << " m" << std::endl;
    return 0;
}

int arm(void)
{
    if(!mavsdk_started)
        return 1;

    log_file_fd << "Arming..." << std::endl;
    const Action::Result arm_result = action->arm();

    if (arm_result != Action::Result::Success) {
        log_file_fd << ERROR_CONSOLE_TEXT << "Arming failed:" << arm_result << NORMAL_CONSOLE_TEXT
                  << std::endl;
        return 1;
    }
    return 0;
}

int healthAllOk(void)
{
    return telemetry->health_all_ok();
}

int takeOff(void)
{
    if(!mavsdk_started)
        return 1;

    log_file_fd << "Taking off..." << std::endl;
    const Action::Result takeoff_result = action->takeoff();
    if (takeoff_result != Action::Result::Success) {
        log_file_fd << ERROR_CONSOLE_TEXT << "Takeoff failed:" << takeoff_result
                  << NORMAL_CONSOLE_TEXT << std::endl;
        return 1;
    }
    return 0;
}

int setTargetCoordinates(double la, double lo, double a, double y)
{
    if(!mavsdk_started)
        return 1;

    std::cout << "Going to altitude " << a <<  " m " << std::endl;
    const Action::Result result = action->goto_location(la, lo, (float) a, (float) y);
    if (result != Action::Result::Success) {
        log_file_fd << ERROR_CONSOLE_TEXT << "Goto location failed:" << result
                  << NORMAL_CONSOLE_TEXT << std::endl;
        return 1;
    }

    std::cout << "Going to location ( " << la << " , " << lo << " ) "
              << a << " m" << std::endl;
    return 0;
}

int setTargetCoordinatesXYZ(double x, double y, double z) {
    double la, lo;

    la = ((initial_drone_la_rad + y / EARTH_RADIUS) * 180.F) / PI;
    lo = ((initial_drone_lo_rad + x / (EARTH_RADIUS * xy_ratio)) * 180.F) / PI;

    return setTargetCoordinates(la, lo, z, 0);
}

double getYaw(void) {
  return drone_yaw;
}
double getRoll(void) {
  return drone_roll;
}
double getPitch(void) {
  return drone_pitch;
}
double getInitialLatitude(void) {
  return initial_drone_la;
}
double getLatitude(void) {
  return drone_la;
}
double getInitialLongitude(void) {
  return initial_drone_lo;
}
double getLongitude(void) {
  return drone_lo;
}
double getTakeOffAltitude(void) {
  const std::pair<Action::Result, float> response = action->get_takeoff_altitude();

  if(response.first != Action::Result::Success) {
    log_file_fd << ERROR_CONSOLE_TEXT << "Get takeoff altitude failed:" << response.first
                << NORMAL_CONSOLE_TEXT << std::endl;
    return -1;
  }
  return response.second;
}
double getInitialAltitude(void) {
  return initial_drone_a;
}
double getAltitude(void) {
  return drone_a;
}

int setTargetLatLong(double la, double lo) {

    return setTargetCoordinates(la, lo, drone_a, 0);
}

int setTargetAltitude(double a)
{
    if(!mavsdk_started)
        return 1;

    log_file_fd << "Going to altitude " << a << "m" << std::endl;

    const Action::Result result = action->goto_location(drone_la, drone_lo, (float) a, 0);
    if (result != Action::Result::Success) {
        log_file_fd << ERROR_CONSOLE_TEXT << "Goto location failed:" << result
                  << NORMAL_CONSOLE_TEXT << std::endl;
        return 1;
    }
    return 0;
}

int land(void)
{
    if(!mavsdk_started)
        return 1;

    log_file_fd << "Landing..." << std::endl;
    const Action::Result land_result = action->terminate();
    if (land_result != Action::Result::Success) {
        log_file_fd << ERROR_CONSOLE_TEXT << "Land failed:" << land_result << NORMAL_CONSOLE_TEXT
                  << std::endl;
        return 1;
    }

    // Check if vehicle is still in air
    while (telemetry->in_air()) {
        log_file_fd << "Vehicle is landing..." << std::endl;
        sleep_for(seconds(1));
    }
    log_file_fd << "Landed!" << std::endl;

    // We are relying on auto-disarming but let's keep watching the telemetry for a bit longer.
    sleep_for(seconds(10));
    log_file_fd << "Finished..." << std::endl;

    return 0;
}
