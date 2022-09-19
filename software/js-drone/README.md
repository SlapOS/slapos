# Javascript drone #

## Presentation ##

* Deploy `user.js` flight script on a drone swarm

* Compile all required libraries to run the flight script

## Parameters ##

* autopilot-ip: IPv4 address to identify the autopilot from the companion board

* drone-guid-list: List of computer id on which flight script must be deployed

* is-a-simulation: Must be set to 'true' to automatically take off during simulation

* multicast-ip: IPv6 of the multicast group of the swarm

* net-if: Network interface used for multicast traffic

* flight-script: URL of user's script to execute to fly drone swarm

* subscriber-guid-list: List of computer id on which subscription script must be deployed

## How it works ##

For each computer listed in `drone-guid-list` and `subscriber-guid-list` a drone SR will be instanciated.
Each instance will return a `instance-path`. Under this path one will find `quickjs binary` in `bin` folder
and `scripts` in `etc` folder.
Run `quickjs binary location` `scripts location`/main.js `scripts location`/user.js .
