import * as mavsdk from "mavsdk";
import * as os from "os";

function fly_drone() {
	if(mavsdk.start("udp://:14540") != 0) {
		return;
	}

	if(mavsdk.arm() != 0) {
		return;
	}

	if(mavsdk.takeOff() != 0) {
		return;
	}

	// Fly in circles for 10 seconds
	os.sleep(10000);

	if(mavsdk.land() != 0) {
		return;
	}

	mavsdk.stop();

	return;
}

fly_drone();
