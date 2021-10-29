#ifndef __MAVSDK_H__
#define __MAVSDK_H__

#ifdef __cplusplus
extern "C" {
#endif
int start(const char * url, const char * log_file, int timeout,
          void (*publishCoordinates)(double, double, float));
int missionPush(
    double latitude_deg,
    double longitude_deg,
    double relative_altitude_m,
    double speed_m_s,
    int is_fly_through,
    double gimbal_pitch_deg,
    double gimbal_yaw_deg);
int uploadMission(void);
int startMission(void);
int arm(void);
int takeOff(void);
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
double getLatitude(void);
double getLongitude(void);
double getAltitude(void);
#ifdef __cplusplus
}
#endif

#endif /* __MAVSDK_H__ */