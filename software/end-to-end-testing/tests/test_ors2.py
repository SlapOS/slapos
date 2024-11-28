import json
import time
import slapos.testing.e2e as e2e
from websocket import create_connection

class WebsocketTestClass(e2e.EndToEndTestCase):
    @classmethod
    def setUpClass(cls):
        try:
            super().setUpClass()

            cls.enb_instance_name = time.strftime('e2e-ors70-enb-%Y-%B-%d-%H:%M:%S')
            cls.product = cls.product.get('https://lab.nexedi.com/nexedi/slapos/-/raw/1.0.371/software/simpleran/software-ors.cfg')

            # Component GUIDs and configurations
            cls.comp_enb = "COMP-4296"

            # Retry configurations
            cls.max_retries = 10
            cls.retry_delay = 180  # seconds

            # Setup instances
            cls.setup_instances()

            cls.waitUntilGreen(cls.enb_instance_name)
            cls.waitUntilGreen(cls.cn_instance_name)

        except Exception as e:
            cls.logger.error("Error during setup: " + str(e))
            # Ensure cleanup
            cls.tearDownClass()
            raise

    @classmethod
    def retry_request(cls, func, *args, **kwargs):
        for attempt in range(cls.max_retries):
            try:
                result = func(*args, **kwargs)
                if result:
                    return result
            except Exception as e:
                cls.logger.error(f"Error on attempt {attempt + 1}: {e}")
            if attempt < cls.max_retries - 1:
                time.sleep(cls.retry_delay)
        return None

    @classmethod
    def setup_instances(cls):
        cls.request_enb()
        cls.request_core_network()
        cls.setup_websocket_connection()

    @classmethod
    def request_enb(cls, custom_params=None):
        cls.logger.info("Request "+ cls.enb_instance_name)

        if custom_params:
            enb_parameters.update(custom_params)

        json_enb_parameters = json.dumps(enb_parameters)

        cls.retry_request(cls.request, cls.product, cls.enb_instance_name,
                          filter_kw={"computer_guid": cls.comp_enb},
                          partition_parameter_kw={'_': json_enb_parameters},
                          software_type='enb')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

class ORSTest(WebsocketTestClass):
    def test_max_rx_sample_db(self):
        custom_params = {"max_rx_sample_db": -99}
        ORSTest.request_enb(custom_params)
        self.waitUntilPromises(ORSTest.enb_instance_name, promise_name="check-rx-saturated", expected=False)
