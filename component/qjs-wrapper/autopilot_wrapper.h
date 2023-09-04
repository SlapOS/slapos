#ifndef __AUTOPILOT_H__
#define __AUTOPILOT_H__

#ifndef DLL_PUBLIC
#define DLL_PUBLIC __attribute__ ((visibility ("default")))
#endif

/*
 * 0. latitude (double, degrees)
 * 1. longitude (double, degrees)
 * 2. absolute altitude (double, meters)
 * 3. relative altitude (double, meters)
 * 4. timestamp (double, milliseconds)
*/
#define POSITION_ARRAY_SIZE 5
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
DLL_PUBLIC int stop();
DLL_PUBLIC int reboot(void);

// Flight state management functions
DLL_PUBLIC int arm(void);
DLL_PUBLIC int takeOff(void);
DLL_PUBLIC int takeOffAndWait(void);
DLL_PUBLIC int triggerParachute(void);

// Flight management functions
DLL_PUBLIC void loiter(double la, double lo, float a, float radius);
DLL_PUBLIC void setAirSpeed_async(float airspeed);
DLL_PUBLIC void setTargetCoordinates(double la, double lo, float a);

// Information functions
DLL_PUBLIC float getAltitude(void);
DLL_PUBLIC float getInitialAltitude(void);
DLL_PUBLIC double getInitialLatitude(void);
DLL_PUBLIC double getInitialLongitude(void);
DLL_PUBLIC int64_t *getPositionArray(void);
DLL_PUBLIC float *getSpeedArray(void);
DLL_PUBLIC double getTakeOffAltitude(void);
DLL_PUBLIC float getYaw(void);
DLL_PUBLIC float getSpeed(void);
DLL_PUBLIC float getClimbRate(void);
DLL_PUBLIC int healthAllOk(void);
DLL_PUBLIC void updateLogAndProjection(void);
#ifdef __cplusplus
}
#endif

#endif /* __AUTOPILOT_H__ */
