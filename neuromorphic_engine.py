"""
NeuroUrja — Leaky Integrate-and-Fire (LIF) Neuromorphic Spiking Engine
Processes 4 cyber-physical microgrid inputs per building:
  1. Demand Forecasts (kW)
  2. Live Occupancy (Headcount & % Capacity)
  3. Equipment Constraints (Battery SOC, Inverter limits, Ramp rates, Essential locks)
  4. Renewable Solar Availability (kW)

Mathematical Model:
  V_m(t) = beta * V_m(t-1) + I_syn(t)
  beta = 0.88 (leakage factor)
  Noise damping: Minor fluctuations leak away exponentially (Agents remain 100% asleep).
  Action Spike: Fired when |V_m(t)| >= V_threshold (1.0).
    - V_m(t) >= +1.0 -> SURPLUS_SPIKE (Donor building ready to export)
    - V_m(t) <= -1.0 -> DEFICIT_SPIKE (Receiver building requests power)
"""

import time
import math
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

# Neuromorphic Hyperparameters
BETA_LEAK = 0.88           # Membrane retention rate (12% leaks away each tick)
V_THRESHOLD = 1.0          # Normalized action potential threshold
V_RESET = 0.0              # Reset potential after spike discharge
REFRACTORY_TICKS = 2       # Refractory period in discrete ticks

@dataclass
class BuildingInputs:
    """The 4 required sensory input streams for a microgrid building."""
    building_id: str
    building_name: str
    demand_forecast_kw: float
    current_load_kw: float
    occupancy_count: int
    max_capacity: int
    solar_generation_kw: float
    solar_capacity_kw: float
    battery_soc_percent: float
    battery_capacity_kwh: float
    battery_max_discharge_kw: float
    essential_service_lock: bool = False
    essential_load_kw: float = 0.0
    cable_thermal_limit_kw: float = 75.0
    indoor_temp_c: float = 23.0
    target_temp_c: float = 22.8


@dataclass
class SpikeEvent:
    """Represents an asynchronous Action Spike fired across the microgrid."""
    spike_id: str
    building_id: str
    timestamp: float
    spike_type: str        # "SURPLUS_SPIKE" | "DEFICIT_SPIKE" | "NOISE_DAMPED"
    membrane_potential: float
    delta_kw: float        # Available surplus (+) or required deficit (-)
    urgency_score: float   # 0.0 to 1.0
    reason: str


class LIFNeuron:
    """
    Leaky Integrate-and-Fire Neuromorphic Spiking Neuron.
    Simulates membrane biophysics to filter noise and trigger event-driven AI.
    """
    def __init__(self, building_id: str, beta: float = BETA_LEAK, threshold: float = V_THRESHOLD):
        self.building_id = building_id
        self.beta = beta
        self.threshold = threshold
        self.v_m = 0.0                  # Membrane potential (-1.5 to +1.5 range)
        self.prev_v_m = 0.0
        self.refractory_counter = 0
        self.total_ticks = 0
        self.spikes_fired = 0
        self.dormant_ticks = 0
        self.history: List[Dict[str, float]] = []
        self.max_history = 120

    def compute_synaptic_current(self, inputs: BuildingInputs) -> float:
        """
        Integrates the 4 sensory inputs into a normalized synaptic injection current I_syn.
        Positive I_syn drives V_m towards SURPLUS_SPIKE (+1.0).
        Negative I_syn drives V_m towards DEFICIT_SPIKE (-1.0).
        """
        # 1. Renewable vs Load Balance (Primary Driver)
        net_power_kw = inputs.solar_generation_kw - inputs.current_load_kw
        nominal_power_scale = max(inputs.solar_capacity_kw, 100.0)
        power_component = net_power_kw / nominal_power_scale  # Typically -1.0 to +1.0

        # 2. Battery Storage Buffer Effect
        # If battery is > 85%, extra bias to discharge/export. If < 25%, urgent need to import.
        soc_deviation = (inputs.battery_soc_percent - 50.0) / 50.0  # -1.0 (empty) to +1.0 (full)
        if inputs.battery_soc_percent > 85.0:
            soc_component = 0.45 * (inputs.battery_soc_percent - 85.0) / 15.0
        elif inputs.battery_soc_percent < 25.0:
            soc_component = -0.55 * (25.0 - inputs.battery_soc_percent) / 25.0
        else:
            soc_component = 0.1 * soc_deviation

        # 3. Occupancy Stress Component
        occupancy_ratio = inputs.occupancy_count / max(inputs.max_capacity, 1)
        # Low occupancy (<15%) implies low internal comfort priority (can donate easily)
        # High occupancy (>80%) implies severe thermal/ventilation urgency
        if occupancy_ratio > 0.70:
            occupancy_component = -0.35 * ((occupancy_ratio - 0.70) / 0.30)
        elif occupancy_ratio < 0.10:
            occupancy_component = +0.25 * ((0.10 - occupancy_ratio) / 0.10)
        else:
            occupancy_component = 0.0

        # 4. Demand Forecast Discrepancy
        # If real load unexpectedly surpasses forecast, drive deficit
        demand_stress = (inputs.demand_forecast_kw - inputs.current_load_kw) / 100.0
        demand_component = max(-0.3, min(0.3, demand_stress * 0.2))

        # Weighted Synaptic Current Injection
        w_p = 0.45
        w_soc = 0.30
        w_occ = 0.15
        w_dem = 0.10

        i_syn = (w_p * power_component) + (w_soc * soc_component) + (w_occ * occupancy_component) + (w_dem * demand_component)
        return i_syn

    def tick(self, inputs: BuildingInputs) -> Optional[SpikeEvent]:
        """
        Executes one discrete neuromorphic time step.
        Returns a SpikeEvent if |V_m| crosses threshold, else None (dormant).
        """
        self.total_ticks += 1
        self.prev_v_m = self.v_m

        # Check refractory period
        if self.refractory_counter > 0:
            self.refractory_counter -= 1
            # In refractory period: membrane relaxes toward reset
            self.v_m = self.beta * self.v_m
            self._record_history(inputs, 0.0, "REFRACTORY")
            return None

        # Compute incoming synaptic current
        i_syn = self.compute_synaptic_current(inputs)

        # Leaky Integration: V_m(t) = beta * V_m(t-1) + I_syn(t)
        self.v_m = (self.beta * self.v_m) + i_syn

        spike: Optional[SpikeEvent] = None
        event_tag = "DORMANT_LEAK"

        # Check for Positive Action Spike (Surplus / Donor)
        if self.v_m >= self.threshold:
            self.spikes_fired += 1
            self.refractory_counter = REFRACTORY_TICKS
            surplus_kw = max(0.0, (inputs.solar_generation_kw - inputs.current_load_kw) + 
                             max(0.0, (inputs.battery_soc_percent - 50.0) * 0.5))
            spike = SpikeEvent(
                spike_id=f"spk-surplus-{self.building_id}-{self.total_ticks}",
                building_id=self.building_id,
                timestamp=time.time(),
                spike_type="SURPLUS_SPIKE",
                membrane_potential=round(self.v_m, 4),
                delta_kw=round(surplus_kw, 2),
                urgency_score=round(min(1.0, (self.v_m - self.threshold) + 0.5), 3),
                reason=f"Solar ({inputs.solar_generation_kw:.1f} kW) + Battery ({inputs.battery_soc_percent:.1f}%) exceeds internal load ({inputs.current_load_kw:.1f} kW)"
            )
            event_tag = "SURPLUS_SPIKE"
            self.v_m = V_RESET

        # Check for Negative Action Spike (Deficit / Receiver)
        elif self.v_m <= -self.threshold:
            self.spikes_fired += 1
            self.refractory_counter = REFRACTORY_TICKS
            deficit_kw = max(0.0, (inputs.current_load_kw - inputs.solar_generation_kw) + 
                            max(0.0, (40.0 - inputs.battery_soc_percent) * 0.8))
            spike = SpikeEvent(
                spike_id=f"spk-deficit-{self.building_id}-{self.total_ticks}",
                building_id=self.building_id,
                timestamp=time.time(),
                spike_type="DEFICIT_SPIKE",
                membrane_potential=round(self.v_m, 4),
                delta_kw=-round(deficit_kw, 2),
                urgency_score=round(min(1.0, abs(self.v_m + self.threshold) + 0.6), 3),
                reason=f"Load ({inputs.current_load_kw:.1f} kW) with {inputs.occupancy_count} occupants strains battery ({inputs.battery_soc_percent:.1f}%)"
            )
            event_tag = "DEFICIT_SPIKE"
            self.v_m = V_RESET

        else:
            self.dormant_ticks += 1

        self._record_history(inputs, i_syn, event_tag)
        return spike

    def _record_history(self, inputs: BuildingInputs, i_syn: float, event_tag: str):
        self.history.append({
            "tick": self.total_ticks,
            "v_m": round(self.v_m, 4),
            "i_syn": round(i_syn, 4),
            "event": event_tag,
            "net_kw": round(inputs.solar_generation_kw - inputs.current_load_kw, 1),
            "soc": round(inputs.battery_soc_percent, 1),
            "occ": inputs.occupancy_count
        })
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def get_dormancy_rate(self) -> float:
        """Calculates percentage of time agent compute remains 100% asleep."""
        if self.total_ticks == 0:
            return 100.0
        return round((self.dormant_ticks / self.total_ticks) * 100.0, 1)


class NeuromorphicEngine:
    """
    Campus-wide Neuromorphic Engine managing LIF neurons across all microgrid nodes.
    Demonstrates Pillar 1: Event-Driven Neuromorphic Spiking vs Clock-Driven Polling.
    """
    def __init__(self):
        self.neurons: Dict[str, LIFNeuron] = {}
        self.buildings_state: Dict[str, BuildingInputs] = {}
        self._init_default_buildings()

    def _init_default_buildings(self):
        # Building A: Student Hostel (High Energy / Idle Donor State)
        self.register_building(BuildingInputs(
            building_id="bldg-hostel-a",
            building_name="Student Hostel Complex A",
            demand_forecast_kw=20.0,
            current_load_kw=18.0,
            occupancy_count=24,        # 4% of 600
            max_capacity=600,
            solar_generation_kw=85.0,  # Peak midday rooftop PV
            solar_capacity_kw=90.0,
            battery_soc_percent=96.0,  # Nearly full 120 kWh bank
            battery_capacity_kwh=120.0,
            battery_max_discharge_kw=60.0,
            essential_service_lock=False,
            essential_load_kw=4.0,
            cable_thermal_limit_kw=75.0,
            indoor_temp_c=24.1,
            target_temp_c=24.0
        ))

        # Building B: Academic & Research Block (Low Energy / High-Demand Receiver State)
        self.register_building(BuildingInputs(
            building_id="bldg-academic-b",
            building_name="Academic & Research Block B",
            demand_forecast_kw=110.0,
            current_load_kw=115.0,
            occupancy_count=480,       # 92% of 520
            max_capacity=520,
            solar_generation_kw=32.0,  # Shaded rooftop array
            solar_capacity_kw=40.0,
            battery_soc_percent=14.0,  # Critical low 90 kWh bank
            battery_capacity_kwh=90.0,
            battery_max_discharge_kw=45.0,
            essential_service_lock=True, # Cryo-Lab cold storage must NEVER drop power
            essential_load_kw=22.0,
            cable_thermal_limit_kw=75.0,
            indoor_temp_c=24.8,
            target_temp_c=22.8
        ))

    def register_building(self, building: BuildingInputs):
        self.buildings_state[building.building_id] = building
        self.neurons[building.building_id] = LIFNeuron(building.building_id)

    def update_building_inputs(self, building_id: str, **kwargs):
        if building_id in self.buildings_state:
            curr = self.buildings_state[building_id]
            data = asdict(curr)
            data.update(kwargs)
            self.buildings_state[building_id] = BuildingInputs(**data)

    def tick_all(self) -> List[SpikeEvent]:
        """Runs one neuromorphic cycle across all buildings, collecting emitted spikes."""
        active_spikes = []
        for b_id, neuron in self.neurons.items():
            inputs = self.buildings_state[b_id]
            spike = neuron.tick(inputs)
            if spike:
                active_spikes.append(spike)
        return active_spikes

    def get_telemetry_snapshot(self) -> Dict[str, Any]:
        """Provides full real-time snapshot for UI visualization and oscilloscope."""
        result = {}
        for b_id, neuron in self.neurons.items():
            inp = self.buildings_state[b_id]
            result[b_id] = {
                "inputs": asdict(inp),
                "v_m": round(neuron.v_m, 4),
                "v_threshold": V_THRESHOLD,
                "beta_leak": BETA_LEAK,
                "dormancy_rate": neuron.get_dormancy_rate(),
                "total_ticks": neuron.total_ticks,
                "spikes_fired": neuron.spikes_fired,
                "recent_history": neuron.history[-30:],
                "net_power_kw": round(inp.solar_generation_kw - inp.current_load_kw, 2)
            }
        return result
