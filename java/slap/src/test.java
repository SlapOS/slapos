import java.util.HashMap;
import java.util.Map;

import org.slapos.slap.*;

/**
 * This class is a simple example or test for libslap-java, showing how to request instances or fetch parameters.
 * @author cedricdesaintmartin
 *
 */
public class test {
	public static void main(String[] args) {
		// Should not be a singleton
		Slap slap = new Slap();
		slap.initializeConnection("http://localhost:5000");
		// We should not have to require
		slap.registerComputer("computer");
		
		String software = "https://gitorious.org/slapos/slapos-software-proactive/blobs/raw/master/software.cfg";
		// Installs a software in the computer
		Supply supply = slap.registerSupply();
		supply.supply(software, "computer");
		
		// Asks an instance of the installed software
		OpenOrder oo = slap.registerOpenOrder();
		Map<String, Object> parameterDict = new HashMap<String, Object>();
		parameterDict.put("credentials", "bububu");
		parameterDict.put("rmURL", "bububu");
		parameterDict.put("nsName", "bububu");
		ComputerPartition cp = oo.request(software, "slappart0", parameterDict, null);
		
		
		String helloworld = "https://gitorious.org/slapos/slapos-software-helloworld/blobs/raw/master/software.cfg";
		// Installs a software in the computer
		Supply supply2 = slap.registerSupply();
		supply2.supply(helloworld, "computer");
		OpenOrder oo2 = slap.registerOpenOrder();
		ComputerPartition cp2 = oo2.request(helloworld, "slappart1", null, null);
		
		
		while (true) {
			try {
				System.out.println((String) cp.getConnectionParameter("useless_parameter"));
			} catch (Exception e) {
				System.out.println(e.getMessage());
			}
			try {
				Thread.sleep(30000);
			} catch (InterruptedException e) {}
			
		}
	}
}

