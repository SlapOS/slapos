#ifndef __MAVSDK_H__
#define __MAVSDK_H__

#ifdef __cplusplus
extern "C" {
#endif
int start(const char * url, const char * log_file, int timeout,
          void (*publishCoordinates)(double, double, float));
int stop(void);
int reboot(void);
int arm(void);
int healthAllOk(void);
int landed(void);
int takeOff(void);
int takeOffAndWait(void);
int setTargetCoordinates(double la, double lo, double a, double y);
int setTargetLatLong(double la, double lo);
int setTargetAltitude(double a);
int setTargetCoordinatesXYZ(double x, double y, double z);
int doParachute(int param);
int loiter(void);
int land(void);
int setAltitude(double altitude);
int setAirspeed(double airspeed);
double getYaw(void);
double getRoll(void);
double getPitch(void);
double getInitialLatitude(void);
double getLatitude(void);
double getInitialLongitude(void);
double getLongitude(void);
double getTakeOffAltitude(void);
double getInitialAltitude(void);
double getAltitude(void);
#ifdef __cplusplus
}
#endif

#endif /* __MAVSDK_H__ */
