#ifndef __MAVSDK_H__
#define __MAVSDK_H__

#ifdef __cplusplus
extern "C" {
#endif
// Connexion management functions
int start(const char * url, const char * log_file, int timeout,
          void (*publishCoordinates)(double, double, float));
int stop(void);
int reboot(void);

// Flight state management functions
int arm(void);
int doParachute(int param);
int loiter(void);
int land(void);
int takeOff(void);
int takeOffAndWait(void);

// Flight management functions
int setAirspeed(double airspeed);
int setAltitude(double altitude);
int setTargetAltitude(double a);
int setTargetCoordinates(double la, double lo, double a, double y);
int setTargetCoordinatesXYZ(double x, double y, double z);
int setTargetLatLong(double la, double lo);

// Information functions
double getAltitude(void);
double getInitialAltitude(void);
double getInitialLatitude(void);
double getInitialLongitude(void);
double getLatitude(void);
double getLongitude(void);
double getPitch(void);
double getRoll(void);
double getTakeOffAltitude(void);
double getYaw(void);
int healthAllOk(void);
int landed(void);
#ifdef __cplusplus
}
#endif

#endif /* __MAVSDK_H__ */
