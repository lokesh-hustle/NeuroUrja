"""
NeuroUrja — Main FastAPI Application & WebSocket Telemetry Server
Coordinates:
  - Leaky Integrate-and-Fire Neuromorphic Engine
  - Autonomous Multi-Agent P2P Coordinator
  - Deterministic Cyber-Physical Security & Hardware Interlocks
  - Real-time WebSocket streaming to Bright Theme Command Center
"""

import asyncio
import os
import json
import time
from typing import List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from backend.neuromorphic_engine import NeuromorphicEngine, BuildingInputs
from backend.security_guardrails import SecurityGuardrails
from backend.agent_coordinator import AgentCoordinator

# Global Singleton Instances
engine = NeuromorphicEngine()
guardrails = SecurityGuardrails()
coordinator = AgentCoordinator(neuromorphic_engine=engine, guardrails=guardrails)

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_json(self, data: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(data)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# Background Neuromorphic Simulation Worker
simulation_running = True
simulation_speed = 1.0  # multiplier

async def neuromorphic_tick_loop():
    """Continuous event-driven neuromorphic loop simulating sensor stream integration."""
    global simulation_running, simulation_speed
    while True:
        try:
            if simulation_running:
                # 1. Step neuromorphic LIF neurons across buildings
                spikes = engine.tick_all()

                # 2. If action spikes fired, wake the Multi-Agent Coordinator
                if spikes:
                    coordinator.process_spikes(spikes)

                # 3. Assemble live telemetry packet
                telemetry = get_full_telemetry_payload()

                # 4. Stream to all connected WebSocket clients
                await manager.broadcast_json(telemetry)

            sleep_duration = max(0.2, 1.0 / simulation_speed)
            await asyncio.sleep(sleep_duration)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[NeuroUrja Loop Error] {e}")
            await asyncio.sleep(1.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: trigger initial background loop
    task = asyncio.create_task(neuromorphic_tick_loop())
    yield
    # Shutdown
    task.cancel()

app = FastAPI(
    title="NeuroUrja Microgrid Platform",
    description="Brain-Inspired Multi-Agent Energy Optimization Platform for Multi-Building Microgrids",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_full_telemetry_payload() -> Dict[str, Any]:
    """Compiles complete state for UI command center."""
    engine_snap = engine.get_telemetry_snapshot()
    coord_snap = coordinator.get_coordinator_summary()
    audit_valid, block_count = guardrails.verify_ledger_integrity()

    # Calculate campus aggregate metrics
    b_hostel = engine_snap.get("bldg-hostel-a", {})
    b_acad = engine_snap.get("bldg-academic-b", {})

    hostel_in = b_hostel.get("inputs", {})
    acad_in = b_acad.get("inputs", {})

    total_solar = hostel_in.get("solar_generation_kw", 0.0) + acad_in.get("solar_generation_kw", 0.0)
    total_load = hostel_in.get("current_load_kw", 0.0) + acad_in.get("current_load_kw", 0.0)

    # Average dormancy rate across neurons
    avg_dormancy = round(
        (b_hostel.get("dormancy_rate", 94.0) + b_acad.get("dormancy_rate", 94.0)) / 2.0, 1
    )

    return {
        "timestamp": time.time(),
        "timestamp_iso": time.strftime('%H:%M:%S', time.localtime()),
        "campus_summary": {
            "total_solar_kw": round(total_solar, 1),
            "total_load_kw": round(total_load, 1),
            "net_campus_kw": round(total_solar - total_load, 1),
            "avg_dormancy_rate": avg_dormancy,
            "total_clean_transferred_kwh": coord_snap["total_clean_energy_transferred_kwh"],
            "total_cost_saved_inr": coord_snap["total_cost_saved_inr"],
            "carbon_offset_kg": round(coord_snap["total_clean_energy_transferred_kwh"] * 0.82, 1),
            "essential_service_uptime": "100.0%",
            "audit_ledger_valid": audit_valid,
            "audit_blocks_count": block_count
        },
        "buildings": engine_snap,
        "coordinator": coord_snap,
        "recent_audits": guardrails.get_recent_audit_logs(limit=15)
    }


# ================= REST API Endpoints =================

@app.get("/api/telemetry")
async def get_telemetry():
    """Returns the full real-time telemetry snapshot."""
    return JSONResponse(content=get_full_telemetry_payload())


class InputUpdateModel(BaseModel):
    building_id: str
    demand_forecast_kw: float | None = None
    current_load_kw: float | None = None
    occupancy_count: int | None = None
    solar_generation_kw: float | None = None
    battery_soc_percent: float | None = None


@app.post("/api/inputs/update")
async def update_inputs(payload: InputUpdateModel):
    """Updates live sensory inputs from the UI Control Deck."""
    updates = {k: v for k, v in payload.dict().items() if v is not None and k != "building_id"}
    engine.update_building_inputs(payload.building_id, **updates)
    return {"status": "SUCCESS", "updated": updates}


@app.post("/api/scenarios/normal")
async def trigger_scenario_normal():
    """
    Scenario 1: Simulate Normal Sunny Midday (Noise Leak Only).
    Slight sensor ripple (3% solar fluctuation, 2 people moving),
    demonstrating that beta=0.88 leaks it away and AI agents remain 100% asleep.
    """
    # Reset to baseline states with slight ripples
    engine.update_building_inputs(
        "bldg-hostel-a",
        solar_generation_kw=82.0,
        current_load_kw=18.5,
        occupancy_count=22,
        battery_soc_percent=95.0
    )
    engine.update_building_inputs(
        "bldg-academic-b",
        solar_generation_kw=34.0,
        current_load_kw=45.0,  # Moderate load, not yet peaking
        occupancy_count=120,   # Moderate occupancy
        battery_soc_percent=60.0
    )
    # Clear active transfer
    coordinator.active_transfer = None
    coordinator.negotiation_state = "DORMANT_MONITORING"
    
    # Reset neurons near 0
    engine.neurons["bldg-hostel-a"].v_m = 0.15
    engine.neurons["bldg-academic-b"].v_m = -0.12

    coordinator._log_message(
        sender_id="scenario-runner",
        sender_name="Scenario Engine",
        receiver_id="all",
        receiver_name="Microgrid Mesh",
        msg_type="SCENARIO_TRIGGERED",
        content="Scenario Initialized: 'Normal Sunny Midday'. Minor sensor noise introduced (V_m < 0.2). Watch noise leak away with beta=0.88 while agents remain 100% dormant."
    )
    return {"scenario": "NORMAL_MIDDAY", "message": "Noise leak active. Agents remain asleep."}


@app.post("/api/scenarios/surge")
async def trigger_scenario_surge():
    """
    Scenario 2: Trigger Lecture Hall Surge + Cloudburst (Fire Spike & P2P Transfer).
    Hostel is idle (4% occupancy, 85 kW solar, 96% battery).
    Academic block surges to 480 students + cloudburst drops solar to 32 kW.
    Emits SURPLUS_SPIKE and DEFICIT_SPIKE -> multi-agent P2P synaptic transfer (65 kW).
    """
    engine.update_building_inputs(
        "bldg-hostel-a",
        solar_generation_kw=85.0,
        current_load_kw=18.0,
        occupancy_count=24,
        battery_soc_percent=96.0
    )
    engine.update_building_inputs(
        "bldg-academic-b",
        solar_generation_kw=32.0,
        current_load_kw=115.0,
        occupancy_count=480,
        battery_soc_percent=14.0
    )

    # Force threshold push
    engine.neurons["bldg-hostel-a"].v_m = 1.05
    engine.neurons["bldg-academic-b"].v_m = -1.10

    # Step immediately to trigger spikes
    spikes = engine.tick_all()
    result = coordinator.process_spikes(spikes)

    return {
        "scenario": "SURGE_AND_CLOUDBURST",
        "spikes_fired": [s.spike_type for s in spikes],
        "result": result
    }


@app.post("/api/scenarios/attack")
async def trigger_scenario_attack():
    """
    Scenario 3: Simulate Spoofed Overload Attack (Test Security Guardrail Block).
    Injects a forged HMAC token with a 140 kW transfer request and malicious injection string.
    Security guardrails detect and block the attack, appending to the immutable ledger.
    """
    result = coordinator.simulate_spoofed_attack()
    return {"scenario": "SPOOFED_ATTACK_TEST", "result": result}


@app.get("/api/audit-log")
async def get_audit_log():
    """Returns the immutable hash-chained audit blocks."""
    valid, count = guardrails.verify_ledger_integrity()
    return {
        "ledger_valid": valid,
        "total_blocks": count,
        "blocks": guardrails.get_recent_audit_logs(limit=30)
    }


@app.get("/api/messages")
async def get_messages():
    """Returns agent conversation and reasoning logs."""
    return coordinator.get_coordinator_summary()["recent_messages"]


@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    """Real-time WebSocket endpoint streaming 1 Hz telemetry to client."""
    await manager.connect(websocket)
    try:
        # Send initial snapshot immediately
        await websocket.send_json(get_full_telemetry_payload())
        while True:
            # Keep connection open and receive client control signals
            data = await websocket.receive_text()
            try:
                cmd = json.loads(data)
                if cmd.get("action") == "SET_SPEED":
                    global simulation_speed
                    simulation_speed = float(cmd.get("speed", 1.0))
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


# Mount static frontend files
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    async def serve_index():
        index_file = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Frontend index.html under construction"}
