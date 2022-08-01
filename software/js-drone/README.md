# Javascript drone #

## Presentation ##

* Deploy `main.js` script on a drone to fly it

* Compile all required libraries to run flight scripts

## Parameters ##

* autopilot-ip: IPv4 address to identify the autpilot from the companion board

* id: User chosen ID for the drone (must be unique in a swarm, will be used as an identifier in multicast communications)

* is-a-simulation: Must be set to 'true' to automatically take off during simulation

* leader-id: Id of the drone chosen to be the leader of the swarm

* multicast-ipv6: IPv6 of the multicast group of the swarm

* net-if: Network interface used for multicast traffic

* drone-id-list: Comma seperated list of the drone IDs of the swarm (recommanded to add the current drone ID)

* flight-script: User script to execute to fly drone swarm

## How it works ##

Run `quickjs binary location` `scripts location`/main.js
