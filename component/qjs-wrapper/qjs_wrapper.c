#include <quickjs/quickjs.h>

#include <open62541/plugin/log_stdout.h>
#include <open62541/plugin/pubsub_udp.h>
#include <open62541/server.h>
#include <open62541/server_config_default.h>

#include "mavsdk_wrapper.h"

#define countof(x) (sizeof(x) / sizeof((x)[0]))

typedef struct PublishedVariable {
    char *name;
    char *description;
    void * UA_RESTRICT pdefaultValue;
    UA_DataType type;
} PublishedVariable;

static UA_Boolean running = true;
static UA_Server *server;

UA_NodeId connectionIdent, publishedDataSetIdent, writerGroupIdent;

static void
addPubSubConnection(UA_Server *server, UA_String *transportProfile,
                    UA_NetworkAddressUrlDataType *networkAddressUrl){
    /* Details about the connection configuration and handling are located
     * in the pubsub connection tutorial */
    UA_PubSubConnectionConfig connectionConfig;
    memset(&connectionConfig, 0, sizeof(connectionConfig));
    connectionConfig.name = UA_STRING("UADP Connection 1");
    connectionConfig.transportProfileUri = *transportProfile;
    connectionConfig.enabled = UA_TRUE;
    UA_Variant_setScalar(&connectionConfig.address, networkAddressUrl,
                         &UA_TYPES[UA_TYPES_NETWORKADDRESSURLDATATYPE]);
    /* Changed to static publisherId from random generation to identify
     * the publisher on Subscriber side */
    connectionConfig.publisherId.numeric = 2234;
    UA_Server_addPubSubConnection(server, &connectionConfig, &connectionIdent);
}

/**
 * **PublishedDataSet handling**
 *
 * The PublishedDataSet (PDS) and PubSubConnection are the toplevel entities and
 * can exist alone. The PDS contains the collection of the published fields. All
 * other PubSub elements are directly or indirectly linked with the PDS or
 * connection. */
static void
addPublishedDataSet(UA_Server *server) {
    /* The PublishedDataSetConfig contains all necessary public
    * information for the creation of a new PublishedDataSet */
    UA_PublishedDataSetConfig publishedDataSetConfig;
    memset(&publishedDataSetConfig, 0, sizeof(UA_PublishedDataSetConfig));
    publishedDataSetConfig.publishedDataSetType = UA_PUBSUB_DATASET_PUBLISHEDITEMS;
    publishedDataSetConfig.name = UA_STRING("Demo PDS");
    /* Create new PublishedDataSet based on the PublishedDataSetConfig. */
    UA_Server_addPublishedDataSet(server, &publishedDataSetConfig, &publishedDataSetIdent);
}

static void
addVariable(UA_Server *server, PublishedVariable varDetails) {
    UA_VariableAttributes attr = UA_VariableAttributes_default;
    UA_Variant_setScalar(&attr.value, varDetails.pdefaultValue, &varDetails.type);
    attr.description = UA_LOCALIZEDTEXT("en-US", varDetails.description);
    attr.displayName = UA_LOCALIZEDTEXT("en-US", varDetails.description);
    attr.dataType = varDetails.type.typeId;
    attr.accessLevel = UA_ACCESSLEVELMASK_READ | UA_ACCESSLEVELMASK_WRITE;

    UA_Server_addVariableNode(server, UA_NODEID_STRING(1, varDetails.name),
                                      UA_NODEID_NUMERIC(0, UA_NS0ID_OBJECTSFOLDER),
                                      UA_NODEID_NUMERIC(0, UA_NS0ID_ORGANIZES),
                                      UA_QUALIFIEDNAME(1, varDetails.description),
                                      UA_NODEID_NUMERIC(0, UA_NS0ID_BASEDATAVARIABLETYPE),
                                      attr, NULL, NULL);
}

static void
writeVariable(UA_Server *server, char *name, void * UA_RESTRICT pvalue,
              UA_DataType type)
{
    UA_NodeId integerNodeId = UA_NODEID_STRING(1, name);

    UA_Variant var;
    UA_Variant_init(&var);
    UA_Variant_setScalar(&var, pvalue, &type);
    UA_Server_writeValue(server, integerNodeId, var);
}

static void
addDataSetField(UA_Server *server, PublishedVariable varDetails) {
    UA_NodeId dataSetFieldIdent;
    UA_DataSetFieldConfig dataSetFieldConfig;
    memset(&dataSetFieldConfig, 0, sizeof(UA_DataSetFieldConfig));
    dataSetFieldConfig.dataSetFieldType = UA_PUBSUB_DATASETFIELD_VARIABLE;
    dataSetFieldConfig.field.variable.fieldNameAlias = UA_STRING(varDetails.description);
    dataSetFieldConfig.field.variable.promotedField = UA_FALSE;
    dataSetFieldConfig.field.variable.publishParameters.publishedVariable =
    UA_NODEID_STRING(1, varDetails.name);
    dataSetFieldConfig.field.variable.publishParameters.attributeId = UA_ATTRIBUTEID_VALUE;
    UA_Server_addDataSetField(server, publishedDataSetIdent,
                              &dataSetFieldConfig, &dataSetFieldIdent);
}

/**
 * **WriterGroup handling**
 *
 * The WriterGroup (WG) is part of the connection and contains the primary
 * configuration parameters for the message creation. */
static void
addWriterGroup(UA_Server *server) {
    /* Now we create a new WriterGroupConfig and add the group to the existing
     * PubSubConnection. */
    UA_WriterGroupConfig writerGroupConfig;
    memset(&writerGroupConfig, 0, sizeof(UA_WriterGroupConfig));
    writerGroupConfig.name = UA_STRING("Demo WriterGroup");
    writerGroupConfig.publishingInterval = 100;
    writerGroupConfig.enabled = UA_FALSE;
    writerGroupConfig.writerGroupId = 100;
    writerGroupConfig.encodingMimeType = UA_PUBSUB_ENCODING_UADP;
    writerGroupConfig.messageSettings.encoding             = UA_EXTENSIONOBJECT_DECODED;
    writerGroupConfig.messageSettings.content.decoded.type = &UA_TYPES[UA_TYPES_UADPWRITERGROUPMESSAGEDATATYPE];
    /* The configuration flags for the messages are encapsulated inside the
     * message- and transport settings extension objects. These extension
     * objects are defined by the standard. e.g.
     * UadpWriterGroupMessageDataType */
    UA_UadpWriterGroupMessageDataType *writerGroupMessage  = UA_UadpWriterGroupMessageDataType_new();
    /* Change message settings of writerGroup to send PublisherId,
     * WriterGroupId in GroupHeader and DataSetWriterId in PayloadHeader
     * of NetworkMessage */
    writerGroupMessage->networkMessageContentMask          = (UA_UadpNetworkMessageContentMask)(UA_UADPNETWORKMESSAGECONTENTMASK_PUBLISHERID |
                                                              (UA_UadpNetworkMessageContentMask)UA_UADPNETWORKMESSAGECONTENTMASK_GROUPHEADER |
                                                              (UA_UadpNetworkMessageContentMask)UA_UADPNETWORKMESSAGECONTENTMASK_WRITERGROUPID |
                                                              (UA_UadpNetworkMessageContentMask)UA_UADPNETWORKMESSAGECONTENTMASK_PAYLOADHEADER);
    writerGroupConfig.messageSettings.content.decoded.data = writerGroupMessage;
    UA_Server_addWriterGroup(server, connectionIdent, &writerGroupConfig, &writerGroupIdent);
    UA_Server_setWriterGroupOperational(server, writerGroupIdent);
    UA_UadpWriterGroupMessageDataType_delete(writerGroupMessage);
}

/**
 * **DataSetWriter handling**
 *
 * A DataSetWriter (DSW) is the glue between the WG and the PDS. The DSW is
 * linked to exactly one PDS and contains additional information for the
 * message generation. */
static void
addDataSetWriter(UA_Server *server) {
    /* We need now a DataSetWriter within the WriterGroup. This means we must
     * create a new DataSetWriterConfig and add call the addWriterGroup function. */
    UA_NodeId dataSetWriterIdent;
    UA_DataSetWriterConfig dataSetWriterConfig;
    memset(&dataSetWriterConfig, 0, sizeof(UA_DataSetWriterConfig));
    dataSetWriterConfig.name = UA_STRING("Demo DataSetWriter");
    dataSetWriterConfig.dataSetWriterId = 62541;
    dataSetWriterConfig.keyFrameCount = 10;
    UA_Server_addDataSetWriter(server, writerGroupIdent, publishedDataSetIdent,
                               &dataSetWriterConfig, &dataSetWriterIdent);
}

static int run(UA_String *transportProfile,
               UA_NetworkAddressUrlDataType *networkAddressUrl) {
    int i;
    UA_Float defaultFloat = 0;
    UA_Double defaultDouble = 0;

    PublishedVariable publishedVariableArray[] = {
        {
            .name = "lattitude",
            .description = "Lattitude",
            .pdefaultValue = &defaultDouble,
            .type = UA_TYPES[UA_TYPES_DOUBLE],
        },
        {
            .name = "longitude",
            .description = "Longitude",
            .pdefaultValue = &defaultDouble,
            .type = UA_TYPES[UA_TYPES_DOUBLE],
        },
        {
            .name = "altitude",
            .description = "Altitude",
            .pdefaultValue = &defaultFloat,
            .type = UA_TYPES[UA_TYPES_FLOAT],
        },
    };

    server = UA_Server_new();
    UA_ServerConfig *config = UA_Server_getConfig(server);
    UA_ServerConfig_setDefault(config);
    UA_ServerConfig_addPubSubTransportLayer(config, UA_PubSubTransportLayerUDPMP());

    addPubSubConnection(server, transportProfile, networkAddressUrl);
    addPublishedDataSet(server);
    for(i = 0; i < countof(publishedVariableArray); i++) {
        addVariable(server, publishedVariableArray[i]);
        addDataSetField(server, publishedVariableArray[i]);
    }
    addWriterGroup(server);
    addDataSetWriter(server);

    UA_StatusCode retval = UA_Server_run(server, &running);

    UA_Server_delete(server);
    return retval == UA_STATUSCODE_GOOD ? EXIT_SUCCESS : EXIT_FAILURE;
}

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

    res = run(&transportProfile, &networkAddressUrl);
    JS_FreeCString(ctx, ipv6);
    JS_FreeCString(ctx, port);

    return JS_NewInt32(ctx, res);
}

void pubsub_set_coordinates(double lattitude, double longitude, float altitude)
{
    writeVariable(server, "lattitude", &lattitude, UA_TYPES[UA_TYPES_DOUBLE]);
    writeVariable(server, "longitude", &longitude, UA_TYPES[UA_TYPES_DOUBLE]);
    writeVariable(server, "altitude", &altitude, UA_TYPES[UA_TYPES_FLOAT]);
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
    return JS_UNDEFINED;
}

static JSValue js_mavsdk_healthAllOk(JSContext *ctx, JSValueConst this_val,
				     int argc, JSValueConst *argv)
{
    return JS_NewBool(ctx, healthAllOk());
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

    return JS_NewInt32(ctx, loiter());
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

static JSValue js_mavsdk_land(JSContext *ctx, JSValueConst this_val,
                              int argc, JSValueConst *argv)
{
    return JS_NewInt32(ctx, land());
}

static const JSCFunctionListEntry js_mavsdk_funcs[] = {
    JS_CFUNC_DEF("start", 3, js_mavsdk_start ),
    JS_CFUNC_DEF("stop", 0, js_mavsdk_stop ),
    JS_CFUNC_DEF("healthAllOk", 0, js_mavsdk_healthAllOk ),
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
