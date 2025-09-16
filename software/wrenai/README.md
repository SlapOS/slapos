# WrenAI

The stack WrenAI is made of 5 components:

* qdrant (data storage)
* wren-engine (Java JDK 21)
* ibis-server (Python 3.11)
* wren-ai-service (Python 3.12)
* wren-ui (NextJS, ReactJS)

Qdrant and wren-engine can run independently, as the other services access them:

* `ibis-server` accesses:
  * `wren-engine`

* `wren-ui` accesses:
  * `wren-engine`
  * `ibis-server`
  * `wren-ai-service`

* `wren-ai-service` accesses:
  * `qdrant`
  * `ibis-server`
  * `wren-ui`

By default, the simplest possible WrenAI stack consist of creating a software that extends from `software/wrenai/software.cfg`, and leaves all the `[custom-profile]` parameters unchanged. That will deploy the 5 components in the same host.

## Deployment in two hosts

To deploy WrenAI in multiple hosts use the parameters defined in the `[custom-profile]` part, in the `software/wrenai/software.cfg`.

A sample deployment could consist of two software entries:

* `software/wrenai-deploy-A/software.cfg`, and
* `software/wrenai-deploy-B/software.cfg`

In the `deploy-A` you could define the section `[custom-profile]` as:

    [custom-profile]
    qdrant_enabled = True
    wren_engine_enabled = True
    ibis_server_enabled = True
    wren_ai_service_enabled = False
    wren_ui_enabled = False

So that it deploys `qdrant`, `wren-engine`, and `ibis-server`. Once deployed you know what is the IPv4 in use and the ports used by those services. With that data you could configure the `deploy-B`:

    [custom-profile]
    qdrant_enabled = False
    qdrant_ipv4 = <ip-from-wrenai-stack-a>
    qdrant_http_port = <qdrant-http-port-from-wrenai-stack-a>
    qdrant_grpc_port = <qdrant-grpc-port-from-wrenai-stack-a>

    wren_engine_enabled  = False
    wren_engine_ipv4 = <ip-from-wrenai-stack-a>
    wren_engine_port = <wren-engine-port-from-wrenai-stack-a>

    ibis_server_enabled = False
    ibis_server_ipv4 = <ip-from-wrenai-stack-a>
    ibis_server_port = <ibis-server-port-from-wrenai-stack-a>

    wren_ai_service_enabled = True
    wren_ui_enabled = True
