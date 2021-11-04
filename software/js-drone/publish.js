/*jslint indent2 */

import { publish } from "{{ qjs_wrapper }}"; //jslint-quiet

const PORT = "4840";
const IPV6 = "{{ ipv6 }}";

publish(IPV6, PORT);
