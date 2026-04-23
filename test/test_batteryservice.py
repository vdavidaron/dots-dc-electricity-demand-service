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

# Attempt to import the service
try:
    from batteryservice import Batteryservice
except ImportError as e:
    print(f"❌ Failed to import service: {e}")
    Batteryservice = None

# --- TEST SETTINGS ---
BROKER_TEST_PORT = 23405  # Using a different port to avoid conflicts
START_DATE_TIME = datetime(2024, 1, 1, 0, 0, 0)
SIMULATION_DURATION_IN_SECONDS = 960

# This ID doesn't need to be in ESDL for the math logic test as it uses fallbacks if missing
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
        
        # Load the local ESDL (even if it's empty of batteries, logic uses fallbacks)
        self.esh = EnergySystemHandler()
        # Use an empty energy system if test.esdl is not found or missing battery
        try:
            self.esh.load_file(os.path.join(current_dir, "test.esdl"))
        except:
            self.esh.create_empty_energy_system("TestSystem", "Test")
        self.energy_system = self.esh.get_energy_system()

    def test_battery_initialization(self):
        """Verify the battery can start and reach the first time step."""
        if Batteryservice is None:
            self.fail("Batteryservice could not be imported!")

        try:
            service = Batteryservice()
            self.assertIsNotNone(service, "Service instance is None")
            print("\n[OK] Batteryservice successfully initialized!")
        except Exception as e:
            self.fail(f"BatteryService crashed during setup: {e}")

    def test_battery_math_logic_charge(self):
        """Tests the charging logic (negative requested power)."""
        service = Batteryservice()
        service.init_calculation_service(self.energy_system)
        service.influx_connector = MagicMock()

        # 1. CHARGING: requested power = -1,000,000 W
        mock_params = {"bess_allocation_w": -1000000.0} 
        
        class MockTimeStep:
            time_period_in_seconds = 900.0
        mock_time_step = MockTimeStep()

        # 2. Call calculation function
        output = service.battery_dispatch(
            param_dict=mock_params, 
            simulation_time=START_DATE_TIME, 
            time_step_number=mock_time_step, 
            esdl_id=TEST_BATTERY_UUID, 
            energy_system=self.energy_system
        )

        # 3. Assert math
        # Initial SoC = 50% of 2,700,000 Wh = 1,350,000 Wh.
        # Charge = 1,000,000 W, eff = 0.95, dt = 0.25h.
        # Added Energy = 1,000,000 * 0.95 * 0.25 = 237,500 Wh.
        # New SoC = 1,350,000 + 237,500 = 1,587,500 Wh.
        # Expected SoC Pct = (1,587,500 / 2,700,000) * 100 = 58.796%
        self.assertAlmostEqual(output.state_of_charge, 58.796, places=3)
        self.assertEqual(output.bess_power_w, -1000000.0)
        
        # Verify max_available_discharge reflects new SoC
        # delivering (1,587,500 * 0.95) / 0.25 = 6,032,500 W (capped by 2.7MW)
        self.assertAlmostEqual(output.max_available_discharge, 2700000.0)
        
        print("\n[OK] Battery charging logic passed!")

    def test_battery_math_logic_discharge(self):
        """Tests the discharging logic (positive requested power)."""
        service = Batteryservice()
        service.init_calculation_service(self.energy_system)
        service.influx_connector = MagicMock()

        # 1. DISCHARGING: requested power = 1,000,000 W
        mock_params = {"bess_allocation_w": 1000000.0} 
        
        class MockTimeStep:
            time_period_in_seconds = 900.0
        mock_time_step = MockTimeStep()

        # 2. Call calculation function
        output = service.battery_dispatch(
            param_dict=mock_params, 
            simulation_time=START_DATE_TIME, 
            time_step_number=mock_time_step, 
            esdl_id=TEST_BATTERY_UUID, 
            energy_system=self.energy_system
        )

        # 3. Assert math
        # Initial SoC = 50% of 2,700,000 Wh = 1,350,000 Wh.
        # Discharge = 1,000,000 W, eff = 0.95, dt = 0.25h.
        # Energy removed from internal storage = (1,000,000 / 0.95) * 0.25 = 263,157.89 Wh.
        # New SoC = 1,350,000 - 263,157.89 = 1,086,842.11 Wh.
        # Expected SoC Pct = (1,086,842.11 / 2,700,000) * 100 = 40.253%
        self.assertAlmostEqual(output.state_of_charge, 40.253, places=3)
        self.assertEqual(output.bess_power_w, 1000000.0)
        
        print("\n[OK] Battery discharging logic passed!")

    def test_battery_clamping_at_full(self):
        """Verify the battery stops charging when 100% full."""
        service = Batteryservice()
        service.init_calculation_service(self.energy_system)
        service.influx_connector = MagicMock()

        # Force state to nearly full
        state = service.battery_states[TEST_BATTERY_UUID]
        state["soc_wh"] = state["capacity_wh"] - 10.0 # Only 10Wh room left
        
        # Request massive charge (-5MW)
        mock_params = {"bess_allocation_w": -5000000.0} 
        
        class MockTimeStep:
            time_period_in_seconds = 900.0
        mock_time_step = MockTimeStep()

        output = service.battery_dispatch(
            param_dict=mock_params, 
            simulation_time=START_DATE_TIME, 
            time_step_number=mock_time_step, 
            esdl_id=TEST_BATTERY_UUID, 
            energy_system=self.energy_system
        )

        # Should be exactly 100% and power should be limited to what fits (10Wh / (0.95 * 0.25h) = 42.1W)
        self.assertAlmostEqual(output.state_of_charge, 100.0, places=5)
        self.assertLess(abs(output.bess_power_w), 50.0) # Should be ~42.1W
        self.assertEqual(output.max_available_charge, 0.0)
        
        print("\n[OK] Battery full-clamping logic passed!")

    def test_battery_clamping_at_empty(self):
        """Verify the battery stops discharging when 0% empty."""
        service = Batteryservice()
        service.init_calculation_service(self.energy_system)
        service.influx_connector = MagicMock()

        # Force state to nearly empty
        state = service.battery_states[TEST_BATTERY_UUID]
        state["soc_wh"] = 10.0 # Only 10Wh left
        
        # Request massive discharge (5MW)
        mock_params = {"bess_allocation_w": 5000000.0} 
        
        class MockTimeStep:
            time_period_in_seconds = 900.0
        mock_time_step = MockTimeStep()

        output = service.battery_dispatch(
            param_dict=mock_params, 
            simulation_time=START_DATE_TIME, 
            time_step_number=mock_time_step, 
            esdl_id=TEST_BATTERY_UUID, 
            energy_system=self.energy_system
        )

        # Should be exactly 0% and power should be limited to what remains (10Wh * 0.95 / 0.25h = 38.0W)
        self.assertAlmostEqual(output.state_of_charge, 0.0, places=5)
        self.assertLess(abs(output.bess_power_w), 50.0) # Should be ~38.0W
        self.assertEqual(output.max_available_discharge, 0.0)
        
        print("\n[OK] Battery empty-clamping logic passed!")

    def test_battery_zero_request(self):
        """Verify the battery does nothing when request is 0."""
        service = Batteryservice()
        service.init_calculation_service(self.energy_system)
        service.influx_connector = MagicMock()

        # 1. Request ZERO power
        mock_params = {"bess_allocation_w": 0.0} 
        
        class MockTimeStep:
            time_period_in_seconds = 900.0
        mock_time_step = MockTimeStep()

        output = service.battery_dispatch(
            param_dict=mock_params, 
            simulation_time=START_DATE_TIME, 
            time_step_number=mock_time_step, 
            esdl_id=TEST_BATTERY_UUID, 
            energy_system=self.energy_system
        )

        # Should remain at 50%
        self.assertAlmostEqual(output.state_of_charge, 50.0, places=5)
        self.assertEqual(output.bess_power_w, 0.0)
        
        print("\n[OK] Battery zero-request logic passed!")

if __name__ == '__main__':
    unittest.main()
