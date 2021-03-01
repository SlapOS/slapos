#ifndef __PUBSUB_SUBSCRIBE_H__
#define __PUBSUB_SUBSCRIBE_H__

#include "pubsub_common.h"

int subscribe(UA_String *transportProfile,
              UA_NetworkAddressUrlDataType *networkAddressUrl,
              UA_Boolean *running);

#endif /* __PUBSUB_SUBSCRIBE_H__ */
