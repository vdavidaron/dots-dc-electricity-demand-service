# Battery Energy Storage System (BESS) Calculation Service

A DOTS-helics calculation service that simulates a Battery Energy Storage System (BESS), managing real-time state of charge (SoC), charging/discharging efficiencies, power constraints, and daily health/capacity degradation.

## Table of Contents
- [Overview](#overview)
- [ESDL Asset Mapping](#esdl-asset-mapping)
- [Calculations & HELICS Federation](#calculations--helics-federation)
  - [Battery State](#battery-state)
  - [Battery Dispatch](#battery-dispatch)
  - [Daily Degradation](#daily-degradation)
- [Data & InfluxDB Logging](#data--influxdb-logging)
- [Project Structure](#project-structure)
- [How to Build & Run](#how-to-build--run)

---

## Overview

The **Battery Service** models the physical behavior of chemical battery storage. It tracks charge accumulation, respects maximum charge and discharge rates, applies round-trip efficiencies, and computes equivalent full cycles to calculate capacity aging/degradation over long co-simulation runs.

The service logic is implemented in [batteryservice.py](src/Batteryservice/batteryservice.py) and inherits from the generated [BatteryserviceBase](src/Batteryservice/batteryservice_base.py) class.

---

## ESDL Asset Mapping

During simulation initialization (in `init_calculation_service`), the service parses the incoming Energy System Description Language (ESDL) topology to configure its battery properties:

- **ESDL Asset Type:** `Battery`
- **Properties Handled:**
  - `capacity`: Total energy capacity of the battery in **Watt-hours (Wh)**. Defaults to `2_700_000.0` Wh (2.7 MWh) if missing or set to `0.0`.
  - `chargeEfficiency`: Efficiency factor of charging (0.0 to 1.0). Defaults to `0.95`.
  - `dischargeEfficiency`: Efficiency factor of discharging (0.0 to 1.0). Defaults to `0.95`.
  - `maxChargeRate`: Maximum charging power capacity in **Watts (W)**. Defaults to ESDL capacity.
  - `maxDischargeRate`: Maximum discharging power capacity in **Watts (W)**. Defaults to ESDL capacity.
- **Initial State:** The battery State of Charge (`soc_wh`) is initialized at **50%** of its capacity to match the starting state of the network's Energy Management System.

---

## Calculations & HELICS Federation

The service defines three calculations configured in [input.json](input.json):

### Battery State
- **Execution Interval:** 900 seconds (15 minutes)
- **Offset:** 0 seconds
- **Purpose:** Publishes physical state limits and current capacity boundaries.
- **HELICS Outputs:**
  - `bess_power_w` (Unit: `W`, Type: `DOUBLE`): The actual power absorbed or injected during the previous step.
  - `state_of_charge` (Unit: `pct`, Type: `DOUBLE`): Current SoC percentage (0% to 100%).
  - `max_available_charge` (Unit: `W`, Type: `DOUBLE`): Maximum power that the battery can absorb in this step, limited by `maxChargeRate` and remaining empty capacity.
  - `max_available_discharge` (Unit: `W`, Type: `DOUBLE`): Maximum power that the battery can inject in this step, limited by `maxDischargeRate` and remaining stored energy.

### Battery Dispatch
- **Execution Interval:** 900 seconds (15 minutes)
- **Offset:** 20 seconds (runs after setpoint optimization)
- **Purpose:** Consumes setpoints from the balancer and updates the internal State of Charge (SoC).
- **HELICS Inputs:**
  - `bess_allocation_w` (Unit: `W`, Type: `DOUBLE`, Published by `ElectricityNetwork`): Setpoint command.
    - **Sign Convention:** **Positive** values = Discharge (BESS injects power). **Negative** values = Charge (BESS absorbs power).
- **Integration Logic:** Computes losses based on charge/discharge efficiency and decreases/increases the internal `soc_wh` accordingly. It also increments the daily energy throughput.

### Daily Degradation
- **Execution Interval:** 86400 seconds (24 hours)
- **Offset:** 0 seconds
- **Purpose:** Simulates daily battery capacity aging and health decay.
- **HELICS Outputs:**
  - `health_capacity_degradation` (Unit: `pct`, Type: `DOUBLE`): The calculated capacity degradation percentage for the day.
- **Aging Model Equation:**
  $$\text{Degradation (\%)} = 0.005\% + (\text{Equivalent Full Cycles} \times 0.02\%)$$
  where:
  $$\text{Equivalent Full Cycles} = \frac{\text{Daily Throughput (Wh)}}{2 \times \text{Capacity (Wh)}}$$
  The battery capacity is updated daily: $\text{Capacity}_{t+1} = \text{Capacity}_t \times (1 - \text{Degradation}/100)$, and the daily throughput is reset.

---

## Data & InfluxDB Logging

To maintain optimal network buffer sizes, the service flushes accumulated metrics **once per simulated day (every 96 steps)**.

The following fields are written to the database under the `Battery` asset ID:
- `state_of_charge` (%): Current battery SoC.
- `bess_power_w` (W): Actual power absorbed (negative) or discharged (positive).
- `Requested_Power_W` (W): Raw incoming balancer command.
- `Max_Available_Charge_W` (W): Available physical charging limit.
- `Max_Available_Discharge_W` (W): Available physical discharging limit.
- `Health_Degradation_Pct` (%): Daily capacity degradation percentage (logged daily).

---

## Project Structure

- [pyproject.toml](pyproject.toml): Package configuration and dependency list.
- [Dockerfile](Dockerfile): Container build using `python:3.13-slim`.
- [code_gen.py](code_gen.py): Code generator invocation script to rebuild base classes.
- [input.json](input.json): Federation calculation specifications.
- **src/Batteryservice/**
  - [batteryservice.py](src/Batteryservice/batteryservice.py): Primary logic overrides.
  - [batteryservice_base.py](src/Batteryservice/batteryservice_base.py): Base class handling HELICS boilerplate.
  - [batteryservice_dataclasses.py](src/Batteryservice/batteryservice_dataclasses.py): Return types for service calculations.

---

## How to Build & Run

### Local Execution
Run the script directly to start the calculation service:
```bash
python src/Batteryservice/batteryservice.py
```

### Docker Build
Build the container image using the local context:
```bash
docker build -t battery-service:latest .
```
