#include <quickjs/quickjs.h>

#include "mavsdk_wrapper.h"
#include "pubsub_publish.h"

static UA_Boolean running = true;

static JSValue js_pubsub_publish(JSContext *ctx, JSValueConst this_val,
                                 int argc, JSValueConst *argv)
{
    const char *ipv6;
    const char *port;
    char urlBuffer[44];
    int res;

    ipv6 = JS_ToCString(ctx, argv[0]);
    port = JS_ToCString(ctx, argv[1]);
    UA_snprintf(urlBuffer, sizeof(urlBuffer), "opc.udp://[%s]:%s/", ipv6, port);

    UA_String transportProfile =
        UA_STRING("http://opcfoundation.org/UA-Profile/Transport/pubsub-udp-uadp");
    UA_NetworkAddressUrlDataType networkAddressUrl =
        {UA_STRING_NULL , UA_STRING(urlBuffer)};

    res = publish(&transportProfile, &networkAddressUrl, &running);
    JS_FreeCString(ctx, ipv6);
    JS_FreeCString(ctx, port);

    return JS_NewInt32(ctx, res);
}

void pubsub_set_coordinates(double lattitude, double longitude, float altitude)
{
    writeDouble("lattitude", lattitude);
    writeDouble("longitude", longitude);
    writeFloat("altitude", altitude);
}

static JSValue js_pubsub_stop(JSContext *ctx, JSValueConst this_val,
                              int argc, JSValueConst *argv)
{
    running = false;
    return JS_NewInt32(ctx, 0);
}

static JSValue js_mavsdk_start(JSContext *ctx, JSValueConst this_val,
                               int argc, JSValueConst *argv)
{
    const char *url;
    const char *log_file;
    int timeout;
    int res;

    url = JS_ToCString(ctx, argv[0]);
    log_file = JS_ToCString(ctx, argv[1]);
    if (JS_ToInt32(ctx, &timeout, argv[2]))
        return JS_EXCEPTION;

    res = start(url, log_file, timeout, pubsub_set_coordinates);
    JS_FreeCString(ctx, url);
    JS_FreeCString(ctx, log_file);

    return JS_NewInt32(ctx, res);
}

static JSValue js_mavsdk_stop(JSContext *ctx, JSValueConst this_val,
                              int argc, JSValueConst *argv)
{
    return JS_NewInt32(ctx, stop());
}

static JSValue js_mavsdk_reboot(JSContext *ctx, JSValueConst this_val,
                                int argc, JSValueConst *argv)
{
    return JS_NewInt32(ctx, reboot());
}

static JSValue js_mavsdk_healthAllOk(JSContext *ctx, JSValueConst this_val,
				     int argc, JSValueConst *argv)
{
    return JS_NewBool(ctx, healthAllOk());
}

static JSValue js_mavsdk_landed(JSContext *ctx, JSValueConst this_val,
				                             int argc, JSValueConst *argv)
{
    return JS_NewBool(ctx, landed());
}

static JSValue js_mavsdk_arm(JSContext *ctx, JSValueConst this_val,
                             int argc, JSValueConst *argv)
{
    return JS_NewInt32(ctx, arm());
}

static JSValue js_mavsdk_setTargetCoordinates(JSContext *ctx,
                                              JSValueConst this_val,
                                              int argc, JSValueConst *argv)
{
    double la_arg_double;
    double lo_arg_double;
    double a_arg_double;
    double y_arg_double;

    if (JS_ToFloat64(ctx, &la_arg_double, argv[0]))
        return JS_EXCEPTION;
    if (JS_ToFloat64(ctx, &lo_arg_double, argv[1]))
        return JS_EXCEPTION;
    if (JS_ToFloat64(ctx, &a_arg_double, argv[2]))
        return JS_EXCEPTION;
    if (JS_ToFloat64(ctx, &y_arg_double, argv[3]))
        return JS_EXCEPTION;

    return JS_NewInt32(ctx, setTargetCoordinates(la_arg_double, lo_arg_double,
                                                 a_arg_double, y_arg_double));
}

static JSValue js_mavsdk_setTargetLatLong(JSContext *ctx, JSValueConst this_val,
                                          int argc, JSValueConst *argv)
{
    double la_arg_double;
    double lo_arg_double;

    if (JS_ToFloat64(ctx, &la_arg_double, argv[0]))
        return JS_EXCEPTION;
    if (JS_ToFloat64(ctx, &lo_arg_double, argv[1]))
        return JS_EXCEPTION;

    return JS_NewInt32(ctx, setTargetLatLong(la_arg_double, lo_arg_double));
}

static JSValue js_mavsdk_setAltitude(JSContext *ctx, JSValueConst this_val,
                                     int argc, JSValueConst *argv)
{
    double altitude;

    if (JS_ToFloat64(ctx, &altitude, argv[0]))
        return JS_EXCEPTION;

    return JS_NewInt32(ctx, setAltitude(altitude));
}

static JSValue js_mavsdk_setAirspeed(JSContext *ctx, JSValueConst this_val,
                                     int argc, JSValueConst *argv)
{
    double altitude;

    if (JS_ToFloat64(ctx, &altitude, argv[0]))
        return JS_EXCEPTION;

    return JS_NewInt32(ctx, setAirspeed(altitude));
}

static JSValue js_mavsdk_getRoll(JSContext *ctx, JSValueConst this_val,
                                 int argc, JSValueConst *argv)
{
    return JS_NewFloat64(ctx, getRoll());
}

static JSValue js_mavsdk_getPitch(JSContext *ctx, JSValueConst this_val,
                                          int argc, JSValueConst *argv)
{
    return JS_NewFloat64(ctx, getPitch());
}

static JSValue js_mavsdk_getYaw(JSContext *ctx, JSValueConst this_val,
                                int argc, JSValueConst *argv)
{
    return JS_NewFloat64(ctx, getYaw());
}

static JSValue js_mavsdk_getInitialLatitude(JSContext *ctx,
                                            JSValueConst this_val,
					                                  int argc, JSValueConst *argv)
{
    return JS_NewFloat64(ctx, getInitialLatitude());
}

static JSValue js_mavsdk_getLatitude(JSContext *ctx, JSValueConst this_val,
                                     int argc, JSValueConst *argv)
{
    return JS_NewFloat64(ctx, getLatitude());
}

static JSValue js_mavsdk_getInitialLongitude(JSContext *ctx,
                                             JSValueConst this_val,
					                                   int argc, JSValueConst *argv)
{
    return JS_NewFloat64(ctx, getInitialLongitude());
}

static JSValue js_mavsdk_getLongitude(JSContext *ctx, JSValueConst this_val,
                                      int argc, JSValueConst *argv)
{
    return JS_NewFloat64(ctx, getLongitude());
}

static JSValue js_mavsdk_getTakeOffAltitude(JSContext *ctx,
                                            JSValueConst this_val,
					                                  int argc, JSValueConst *argv)
{
    return JS_NewFloat64(ctx, getTakeOffAltitude());
}

static JSValue js_mavsdk_getInitialAltitude(JSContext *ctx,
                                            JSValueConst this_val,
                                            int argc, JSValueConst *argv)
{
    return JS_NewFloat64(ctx, getInitialAltitude());
}

static JSValue js_mavsdk_getAltitude(JSContext *ctx, JSValueConst this_val,
                                     int argc, JSValueConst *argv)
{
    return JS_NewFloat64(ctx, getAltitude());
}

static JSValue js_mavsdk_loiter(JSContext *ctx, JSValueConst this_val,
                                int argc, JSValueConst *argv)
{
    JSValueConst options;
    JSValue val;
    double radius = 10;

    if(argc >= 1) {
        options = argv[1];
	      val = JS_GetPropertyStr(ctx, options, "radius");
	      if(JS_ToFloat64(ctx, &radius, val)) {
	          return JS_EXCEPTION;
	      }
	      JS_FreeValue(ctx, val);
    }
    return JS_NewInt32(ctx, loiter(radius));
}

static JSValue js_mavsdk_doParachute(JSContext *ctx, JSValueConst this_val,
                                     int argc, JSValueConst *argv)
{
    int param;

    if (JS_ToInt32(ctx, &param, argv[0]))
        return JS_EXCEPTION;

    return JS_NewInt32(ctx, doParachute(param));
}

static JSValue js_mavsdk_setTargetCoordinatesXYZ(JSContext *ctx,
                                                 JSValueConst this_val,
                                                 int argc, JSValueConst *argv)
{
    double x_arg_double;
    double y_arg_double;
    double z_arg_double;

    if (JS_ToFloat64(ctx, &x_arg_double, argv[0]))
        return JS_EXCEPTION;
    if (JS_ToFloat64(ctx, &y_arg_double, argv[1]))
        return JS_EXCEPTION;
    if (JS_ToFloat64(ctx, &z_arg_double, argv[2]))
        return JS_EXCEPTION;

    return JS_NewInt32(ctx, setTargetCoordinatesXYZ(x_arg_double, y_arg_double,
                                                    z_arg_double));
}

static JSValue js_mavsdk_setTargetAltitude(JSContext *ctx, JSValueConst this_val,
                                           int argc, JSValueConst *argv)
{
    double a_arg_double;

    if (JS_ToFloat64(ctx, &a_arg_double, argv[0]))
        return JS_EXCEPTION;

    return JS_NewInt32(ctx, setTargetAltitude(a_arg_double));
}

static JSValue js_mavsdk_takeOff(JSContext *ctx, JSValueConst this_val,
                                 int argc, JSValueConst *argv)
{
    return JS_NewInt32(ctx, takeOff());
}

static JSValue js_mavsdk_takeOffAndWait(JSContext *ctx, JSValueConst this_val,
                                 int argc, JSValueConst *argv)
{
    return JS_NewInt32(ctx, takeOffAndWait());
}

static JSValue js_mavsdk_land(JSContext *ctx, JSValueConst this_val,
                              int argc, JSValueConst *argv)
{
    return JS_NewInt32(ctx, land());
}

static const JSCFunctionListEntry js_mavsdk_funcs[] = {
    JS_CFUNC_DEF("start", 3, js_mavsdk_start ),
    JS_CFUNC_DEF("stop", 0, js_mavsdk_stop ),
    JS_CFUNC_DEF("reboot", 0, js_mavsdk_reboot ),
    JS_CFUNC_DEF("healthAllOk", 0, js_mavsdk_healthAllOk ),
    JS_CFUNC_DEF("landed", 0, js_mavsdk_landed ),
    JS_CFUNC_DEF("arm", 0, js_mavsdk_arm ),
    JS_CFUNC_DEF("setTargetCoordinates", 4, js_mavsdk_setTargetCoordinates ),
    JS_CFUNC_DEF("setTargetLatLong", 2, js_mavsdk_setTargetLatLong ),
    JS_CFUNC_DEF("setAltitude", 1, js_mavsdk_setAltitude ),
    JS_CFUNC_DEF("setAirspeed", 1, js_mavsdk_setAirspeed ),
    JS_CFUNC_DEF("loiter", 0, js_mavsdk_loiter ),
    JS_CFUNC_DEF("doParachute", 1, js_mavsdk_doParachute ),
    JS_CFUNC_DEF("setTargetCoordinatesXYZ", 3, js_mavsdk_setTargetCoordinatesXYZ ),
    JS_CFUNC_DEF("setTargetAltitude", 1, js_mavsdk_setTargetAltitude ),
    JS_CFUNC_DEF("getRoll", 0, js_mavsdk_getRoll ),
    JS_CFUNC_DEF("getPitch", 0, js_mavsdk_getPitch ),
    JS_CFUNC_DEF("getYaw", 0, js_mavsdk_getYaw ),
    JS_CFUNC_DEF("getInitialLatitude", 0, js_mavsdk_getInitialLatitude ),
    JS_CFUNC_DEF("getLatitude", 0, js_mavsdk_getLatitude ),
    JS_CFUNC_DEF("getInitialLongitude", 0, js_mavsdk_getInitialLongitude ),
    JS_CFUNC_DEF("getLongitude", 0, js_mavsdk_getLongitude ),
    JS_CFUNC_DEF("getTakeOffAltitude", 0, js_mavsdk_getTakeOffAltitude ),
    JS_CFUNC_DEF("getInitialAltitude", 0, js_mavsdk_getInitialAltitude ),
    JS_CFUNC_DEF("getAltitude", 0, js_mavsdk_getAltitude ),
    JS_CFUNC_DEF("takeOff", 0, js_mavsdk_takeOff ),
    JS_CFUNC_DEF("takeOffAndWait", 0, js_mavsdk_takeOffAndWait ),
    JS_CFUNC_DEF("land", 0, js_mavsdk_land ),
    JS_CFUNC_DEF("publish", 2, js_pubsub_publish ),
    JS_CFUNC_DEF("stopPubsub", 0, js_pubsub_stop ),
};

static int js_mavsdk_init(JSContext *ctx, JSModuleDef *m)
{
    return JS_SetModuleExportList(ctx, m, js_mavsdk_funcs,
                                  countof(js_mavsdk_funcs));
}

JSModuleDef *js_init_module(JSContext *ctx, const char *module_name)
{
    JSModuleDef *m;
    m = JS_NewCModule(ctx, module_name, js_mavsdk_init);
    if (!m)
        return NULL;
    JS_AddModuleExportList(ctx, m, js_mavsdk_funcs, countof(js_mavsdk_funcs));
    return m;
}
