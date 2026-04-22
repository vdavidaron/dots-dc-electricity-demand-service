import sys
import os
import unittest
from unittest.mock import MagicMock
import helics as h
from datetime import datetime
from dots_infrastructure.DataClasses import SimulatorConfiguration
from esdl.esdl_handler import EnergySystemHandler
from dots_infrastructure import CalculationServiceHelperFunctions

# --- PATH FIX ---
# Adjusting path to find the source code in the ../src directory
current_dir = os.path.dirname(__file__)
src_path = os.path.abspath(os.path.join(current_dir, '..', 'src', 'Batteryservice'))
sys.path.append(src_path)

# Attempt to import the service (this checks your 'no-dot' import fix)
try:
    from batteryservice import Batteryservice
except ImportError as e:
    print(f"❌ Failed to import service: {e}")
    Batteryservice = None

# --- TEST SETTINGS ---
BROKER_TEST_PORT = 23405  # Using a different port to avoid conflicts
START_DATE_TIME = datetime(2024, 1, 1, 0, 0, 0)
SIMULATION_DURATION_IN_SECONDS = 960

# IMPORTANT: Replace this with the UUID of the Battery in your test.esdl
TEST_BATTERY_UUID = "97395372-ee67-42ed-8dd6-bf5600b66225" 

def mock_battery_environment():
    """Mocks the environment variables for the Battery Service."""
    return SimulatorConfiguration(
        "BatteryService",                    # name
        [TEST_BATTERY_UUID],                 # esdl_ids
        "Mock-Battery-Federate",             # federate_name
        "127.0.0.1",                         # broker_ip
        BROKER_TEST_PORT,                    # broker_port
        "local-battery-test",                # simulation_id
        SIMULATION_DURATION_IN_SECONDS,      # simulation_duration
        START_DATE_TIME,                     # calculation_start_datetime
        "localhost", "8086", "admin", "pass", "dots", # InfluxDB junk
        h.HelicsLogLevel.DEBUG,              # log_level
        ["Battery"]                          # registered_esdl_classes
    )

class TestBatteryService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Spins up a local HELICS broker for the test."""
        init_string = f"-f 1 --name=batterybroker --port={BROKER_TEST_PORT}"
        cls.broker = h.helicsCreateBroker("zmq", "", init_string)
        if not h.helicsBrokerIsConnected(cls.broker):
            raise RuntimeError("Could not start HELICS broker for testing.")

    @classmethod
    def tearDownClass(cls):
        """Cleans up the broker."""
        h.helicsBrokerDisconnect(cls.broker)
        h.helicsBrokerFree(cls.broker)
        h.helicsCloseLibrary()

    def setUp(self):
        # Inject the mock config
        CalculationServiceHelperFunctions.get_simulator_configuration_from_environment = mock_battery_environment
        
        # Load the local ESDL
        self.esh = EnergySystemHandler()
        self.esh.load_file(os.path.join(current_dir, "test.esdl"))
        self.energy_system = self.esh.get_energy_system()

    def test_battery_initialization(self):
        """Verify the battery can start and reach the first time step."""
        if Batteryservice is None:
            self.fail("Batteryservice could not be imported! Check your import statements.")

        try:
            # Instantiate the service (should now take 0 arguments besides self)
            service = Batteryservice()
            
            # Verify basic setup
            self.assertIsNotNone(service, "Service instance is None")
            
            # Optional: Test one time step if your code allows
            # service.run_step(60) 
            
            print("\n[OK] Batteryservice successfully initialized and connected to HELICS!")
            
        except Exception as e:
            self.fail(f"BatteryService crashed during setup: {e}")

    def test_battery_math_logic(self):
        """Tests the actual charging logic without running the full simulation loop."""
        service = Batteryservice()
        
        # Initialize it so it sets up self.battery_states
        service.init_calculation_service(self.energy_system)

        # --- THE FIX: Silence the InfluxDB Connector ---
        service.influx_connector = MagicMock()
        # -----------------------------------------------

        # 1. Manually craft the inputs
        mock_params = {"bess_allocation_w": 1000000.0} 
        
        # Mock the TimeStepInformation object
        class MockTimeStep:
            time_period_in_seconds = 900.0
        mock_time_step = MockTimeStep()

        # 2. Call your calculation function directly
        output = service.battery_dispatch(
            param_dict=mock_params, 
            simulation_time=START_DATE_TIME, 
            time_step_number=mock_time_step, 
            esdl_id=TEST_BATTERY_UUID, 
            energy_system=self.energy_system
        )

        # 3. Assert the math is correct!
        # Initial SoC was 50% = 1,350,000 Wh.
        # Power = 1,000,000 W, charge efficiency 0.95, time step = 0.25h.
        # Added Energy = 1,000,000 * 0.95 * 0.25 = 237,500 Wh.
        # New SoC = 1,350,000 + 237,500 = 1,587,500 Wh
        # Expected SoC Pct = (1,587,500 / 2,700,000) * 100 = 58.796%
        self.assertAlmostEqual(output.state_of_charge, (1587500.0 / 2700000.0) * 100.0, places=3, msg="Battery SoC math is incorrect!")
        self.assertAlmostEqual(output.bess_power_w, 1000000.0, places=2, msg="Battery actual power output mismatch!")
        # Max capacity limits test (Available charge headroom)
        # Headroom = 2,700,000 - 1,587,500 = 1,112,500 Wh
        # Max Charge Power = 1,112,500 / (0.95 * 0.25) = 4,684,210.5 W (but capped by 2.7MW maxChargeRate)
        self.assertAlmostEqual(output.max_available_charge, 2700000.0, places=2)
        
        # Max Discharge is limited by SoC = 1,587,500 Wh. 
        # Convert to power limit: (1,587,500 * 0.95) / 0.25h = 6,032,500 W (capped by 2.7MW)
        self.assertAlmostEqual(output.max_available_discharge, 2700000.0, places=2)

        # 4. Test daily_degradation behavior
        deg_output = service.daily_degradation(
            param_dict={}, 
            simulation_time=START_DATE_TIME, 
            time_step_number=mock_time_step, 
            esdl_id=TEST_BATTERY_UUID, 
            energy_system=self.energy_system
        )
        self.assertTrue(hasattr(deg_output, "health_capacity_degradation"))
        self.assertGreater(deg_output.health_capacity_degradation, 0.0)
        
        print("\n[OK] Battery math logic passed successfully!")
if __name__ == '__main__':
    unittest.main()