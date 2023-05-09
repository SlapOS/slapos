#ifndef __MAVSDK_H__
#define __MAVSDK_H__

#if defined _WIN32 || defined __CYGWIN__
  #ifdef BUILDING_DLL
    #ifdef __GNUC__
      #define DLL_PUBLIC __attribute__ ((dllexport))
    #else
      #define DLL_PUBLIC __declspec(dllexport) // Note: actually gcc seems to also supports this syntax.
    #endif
  #else
    #ifdef __GNUC__
      #define DLL_PUBLIC __attribute__ ((dllimport))
    #else
      #define DLL_PUBLIC __declspec(dllimport) // Note: actually gcc seems to also supports this syntax.
    #endif
  #endif
  #define DLL_LOCAL
#else
  #if __GNUC__ >= 4
    #define DLL_PUBLIC __attribute__ ((visibility ("default")))
    #define DLL_LOCAL  __attribute__ ((visibility ("hidden")))
  #else
    #define DLL_PUBLIC
    #define DLL_LOCAL
  #endif
#endif

/*
 * 0. latitude (double, degrees)
 * 1. longitude (double, degrees)
 * 2. absolute altitude (double, meters)
 * 3. relative altitude (double, meters)
*/
#define POSITION_ARRAY_SIZE 4
/*
 * 0. yaw angle (float, degrees)
 * 1. air speed (float, m/s)
 * 2. climb rate (float, m/s)
*/
#define SPEED_ARRAY_SIZE 3

#ifdef __cplusplus
extern "C" {
#endif
#include <stdint.h>
// Connexion management functions
DLL_PUBLIC int start(const char * ip, int port, const char * log_file, int timeout);
DLL_PUBLIC int stop(bool shutdown);
DLL_PUBLIC int reboot(void);

// Flight state management functions
DLL_PUBLIC int arm(void);
DLL_PUBLIC int takeOff(void);
DLL_PUBLIC int takeOffAndWait(void);
DLL_PUBLIC int triggerParachute(void);

// Flight management functions
DLL_PUBLIC int loiter(float radius);
DLL_PUBLIC int setAirspeed(float airspeed);
DLL_PUBLIC int setTargetCoordinates(double la, double lo, float a);

// Information functions
DLL_PUBLIC float getAltitude(void);
DLL_PUBLIC float getAltitudeRel(void);
DLL_PUBLIC float getInitialAltitude(void);
DLL_PUBLIC double getInitialLatitude(void);
DLL_PUBLIC double getInitialLongitude(void);
DLL_PUBLIC double getLatitude(void);
DLL_PUBLIC double getLongitude(void);
DLL_PUBLIC double *getPositionArray(void);
DLL_PUBLIC float *getSpeedArray(void);
DLL_PUBLIC double getTakeOffAltitude(void);
DLL_PUBLIC float getYaw(void);
DLL_PUBLIC float getSpeed(void);
DLL_PUBLIC float getClimbRate(void);
DLL_PUBLIC int healthAllOk(void);
#ifdef __cplusplus
}
#endif

#endif /* __MAVSDK_H__ */
