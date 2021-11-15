#ifndef __PUBSUB_PUBLISH_H__
#define __PUBSUB_PUBLISH_H__

#include "pubsub_common.h"

void writeFloat(char *name, float value);
void writeDouble(char *name, double value);
int publish(UA_String *transportProfile,
            UA_NetworkAddressUrlDataType *networkAddressUrl,
            UA_Boolean *running);

#endif /* __PUBSUB_PUBLISH_H__ */
