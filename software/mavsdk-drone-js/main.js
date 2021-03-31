import * as mavsdk from "mavsdk";
import * as os from "os";


function fly_drone() {
	if(mavsdk.start("udp://169.0.1.2:7909") != 0) {
		return;
	}
	os.sleep(1000);

	if(mavsdk.arm() != 0) {
		return;
	}
	os.sleep(1000);

	if(mavsdk.takeOff() != 0) {
		return;
	}
	os.sleep(80000);

        console.log("setTargetAltitude(100)");
	if(mavsdk.setTargetAltitude(100) != 0) {
		return;
	}

	os.sleep(80000);
        console.log("setTargetAltitude(30)");
	if(mavsdk.setTargetAltitude(30) != 0) {
		return;
	}
	os.sleep(80000);
        console.log("setTargetAltitude(80)");
	if(mavsdk.setTargetAltitude(80) != 0) {
		return;
	}

	// Fly in circles for 5 minutes
	os.sleep(300000);

	if(mavsdk.land() != 0) {
		return;
	}

	mavsdk.stop();

	return;
}

fly_drone();
