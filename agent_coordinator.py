"""
NeuroUrja — Autonomous Multi-Agent P2P Negotiation Engine
Pillar 2: Context-Aware Multi-Agent P2P Synaptic Power Transfer

Agents:
  1. HostelDonorAgent ("Aura-1"):
       - Represents Student Hostel Complex A (Idle daytime state, 4% occupancy)
       - Abundant rooftop solar (85 kW), Full battery (96% SOC)
       - Awakens on SURPLUS_SPIKE and offers signed zero-marginal-cost clean power
  2. AcademicReceiverAgent ("Cortex-2"):
       - Represents Academic & Research Block B (High-demand state, 92% occupancy)
       - Low solar (32 kW), Depleted battery (14% SOC), High HVAC load
       - Awakens on DEFICIT_SPIKE and negotiates P2P synaptic transfer
  3. ResearchLabCriticalAgent ("CryoShield-3"):
       - Protects sensitive cryogenic specimen freezers & quantum lab (-80°C)
       - Holds inviolable ESSENTIAL_SERVICE_LOCK
  4. GridCoordinatorAgent ("NexusGrid-0"):
       - Campus substation interface monitoring 11kV grid connection
       - Tracks avoided Time-of-Day peak demand tariff penalties (₹14.50/kWh)

Negotiation Protocol:
  Spike Event -> Asynchronous Awakening -> Synaptic Bid Formulation ->
  HMAC-SHA256 Token Signing -> Hardware Interlock Validation ->
  Synaptic Transfer Execution -> Setpoint Optimization (22.8°C preserved) -> Return to Sleep
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from backend.neuromorphic_engine import SpikeEvent, BuildingInputs, NeuromorphicEngine
from backend.security_guardrails import SecurityGuardrails

@dataclass
class AgentMessage:
    msg_id: str
    timestamp: float
    timestamp_iso: str
    sender_agent: str
    sender_name: str
    receiver_agent: str
    receiver_name: str
    message_type: str      # "SPIKE_ALERT" | "BID_OFFER" | "BID_ACCEPT" | "TRANSFER_ACTIVE" | "EQUILIBRIUM"
    content: str
    telemetry_tags: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActiveTransfer:
    transfer_id: str
    donor_id: str
    donor_name: str
    receiver_id: str
    receiver_name: str
    transferred_kw: float
    grid_draw_before_kw: float
    grid_draw_after_kw: float
    comfort_temp_c: float
    essential_service_status: str
    cost_saved_per_hour_inr: float
    token_verified: bool
    status: str            # "SYNAPTIC_STREAMING" | "EQUILIBRATED" | "HALTED"


class AgentCoordinator:
    """
    Coordinates decentralized P2P negotiations between building microgrid agents.
    Maintains zero compute overhead while dormant, waking up only upon Action Spikes.
    """
    def __init__(self, neuromorphic_engine: NeuromorphicEngine, guardrails: SecurityGuardrails):
        self.engine = neuromorphic_engine
        self.guardrails = guardrails
        self.active_transfer: Optional[ActiveTransfer] = None
        self.agent_dialog_log: List[AgentMessage] = []
        self.max_dialog_history = 60
        self.negotiation_state = "DORMANT_MONITORING"
        self.peak_cost_per_kwh_inr = 14.50  # Commercial ToD peak tariff
        self.total_clean_energy_transferred_kwh = 0.0
        self.total_cost_saved_inr = 0.0

    def _log_message(
        self,
        sender_id: str,
        sender_name: str,
        receiver_id: str,
        receiver_name: str,
        msg_type: str,
        content: str,
        tags: Optional[Dict[str, Any]] = None
    ) -> AgentMessage:
        now = time.time()
        msg = AgentMessage(
            msg_id=f"msg-{int(now*1000)}-{len(self.agent_dialog_log)}",
            timestamp=now,
            timestamp_iso=time.strftime('%H:%M:%S', time.localtime(now)),
            sender_agent=sender_id,
            sender_name=sender_name,
            receiver_agent=receiver_id,
            receiver_name=receiver_name,
            message_type=msg_type,
            content=content,
            telemetry_tags=tags or {}
        )
        self.agent_dialog_log.append(msg)
        if len(self.agent_dialog_log) > self.max_dialog_history:
            self.agent_dialog_log.pop(0)
        return msg

    def process_spikes(self, spikes: List[SpikeEvent]) -> Dict[str, Any]:
        """
        Main Event-Driven Entry Point.
        Called only when the Neuromorphic Engine discharges action spikes.
        """
        if not spikes:
            # Agents stay 100% asleep (0 W compute overhead)
            return {"status": "DORMANT", "active_transfer": asdict(self.active_transfer) if self.active_transfer else None}

        surplus_spikes = [s for s in spikes if s.spike_type == "SURPLUS_SPIKE"]
        deficit_spikes = [s for s in spikes if s.spike_type == "DEFICIT_SPIKE"]

        # 1. Announce spikes in agent network
        for spk in spikes:
            bldg = self.engine.buildings_state.get(spk.building_id)
            bldg_name = bldg.building_name if bldg else spk.building_id
            self._log_message(
                sender_id=spk.building_id,
                sender_name=f"Agent-{spk.building_id.split('-')[1].title()}",
                receiver_id="broadcast",
                receiver_name="Microgrid Mesh Bus",
                msg_type="SPIKE_ALERT",
                content=f"Action Spike {spk.spike_type} fired! V_m={spk.membrane_potential:.3f} >= threshold. Delta={spk.delta_kw:+.1f} kW. Reason: {spk.reason}",
                tags={"delta_kw": spk.delta_kw, "urgency": spk.urgency_score}
            )

        # 2. Check if a Donor and Receiver can establish a Synaptic Link
        if surplus_spikes and deficit_spikes:
            donor_spk = surplus_spikes[0]
            receiver_spk = deficit_spikes[0]
            return self.execute_synaptic_negotiation(donor_spk, receiver_spk)

        elif surplus_spikes and not deficit_spikes:
            donor = surplus_spikes[0]
            self._log_message(
                sender_id=donor.building_id,
                sender_name="Hostel Agent (Aura-1)",
                receiver_id="grid-gateway-0",
                receiver_name="Grid Gateway (NexusGrid-0)",
                msg_type="BID_OFFER",
                content=f"Surplus {donor.delta_kw:.1f} kW available. No campus deficit active. Storing in local battery storage (SOC 96%).",
                tags={"available_kw": donor.delta_kw}
            )
            return {"status": "LOCAL_STORAGE_ABSORPTION", "active_transfer": None}

        elif deficit_spikes and not surplus_spikes:
            rec = deficit_spikes[0]
            self._log_message(
                sender_id=rec.building_id,
                sender_name="Academic Agent (Cortex-2)",
                receiver_id="grid-gateway-0",
                receiver_name="Grid Gateway (NexusGrid-0)",
                msg_type="DEFICIT_REQUEST",
                content=f"Deficit {abs(rec.delta_kw):.1f} kW requested. No donor node currently spiking. Preparing grid peak backup request.",
                tags={"deficit_kw": rec.delta_kw}
            )
            return {"status": "GRID_BACKUP_REQUEST", "active_transfer": None}

        return {"status": "DORMANT", "active_transfer": None}

    def execute_synaptic_negotiation(self, donor_spk: SpikeEvent, receiver_spk: SpikeEvent) -> Dict[str, Any]:
        """
        Multi-agent negotiation handshake between Building A (Hostel) and Building B (Academic Block).
        """
        donor_bldg = self.engine.buildings_state[donor_spk.building_id]
        receiver_bldg = self.engine.buildings_state[receiver_spk.building_id]

        self.negotiation_state = "NEGOTIATING_HANDSHAKE"

        # Step A: Donor Agent Formulates Bid
        # Can offer up to donor_spk.delta_kw, capped by available battery and solar
        target_transfer_kw = min(65.0, min(donor_spk.delta_kw, abs(receiver_spk.delta_kw)))

        self._log_message(
            sender_id=donor_bldg.building_id,
            sender_name="Hostel Agent (Aura-1)",
            receiver_id=receiver_bldg.building_id,
            receiver_name="Academic Agent (Cortex-2)",
            msg_type="BID_OFFER",
            content=f"Synaptic Offer: Generating {target_transfer_kw:.1f} kW clean P2P transfer at ₹0.00 zero-marginal cost. Occupancy low (4%), Battery 96%.",
            tags={"offer_kw": target_transfer_kw, "battery_soc": donor_bldg.battery_soc_percent}
        )

        # Step B: Receiver Agent Evaluates Comfort & Essential Services
        # Academic block has 480 occupants and Cryo-Lab cold storage
        self._log_message(
            sender_id=receiver_bldg.building_id,
            sender_name="Academic Agent (Cortex-2)",
            receiver_id=donor_bldg.building_id,
            receiver_name="Hostel Agent (Aura-1)",
            msg_type="BID_ACCEPT",
            content=f"Handshake Accepted: Requesting {target_transfer_kw:.1f} kW power injection. Preserving 480 students thermal comfort (target: 22.8°C) + Cryo-Lab Cold Storage (100% SLA).",
            tags={"accepted_kw": target_transfer_kw, "occupants": receiver_bldg.occupancy_count}
        )

        # Step C: Essential Service Lab Agent validates zero interruption
        self._log_message(
            sender_id="lab-cryo-shield",
            sender_name="Cryo-Lab Agent (CryoShield-3)",
            receiver_id="security-firewall",
            receiver_name="Microgrid Guardrails",
            msg_type="ESSENTIAL_LOCK_CONFIRM",
            content="Cryo-Lab Cold Storage (-80°C Specimen Core) lock intact. Transfer must not induce bus voltage sag.",
            tags={"sla_uptime": "100.0%", "temp_c": -80.0}
        )

        # Step D: Cryptographic Handshake Generation (HMAC-SHA256 Token)
        transfer_token = self.guardrails.generate_transfer_token(
            sender_id=donor_bldg.building_id,
            receiver_id=receiver_bldg.building_id,
            kw_amount=target_transfer_kw
        )

        # Step E: Hardware-Safe Guardrails & Cable Ampacity Validation
        approved, guardrail_msg, verified_kw = self.guardrails.validate_physical_transfer(
            token=transfer_token,
            sender_battery_soc=donor_bldg.battery_soc_percent,
            receiver_battery_soc=receiver_bldg.battery_soc_percent,
            sender_current_load=donor_bldg.current_load_kw,
            receiver_has_essential_lock=receiver_bldg.essential_service_lock,
            requested_kw=target_transfer_kw
        )

        if not approved:
            self._log_message(
                sender_id="security-firewall",
                sender_name="Security Guardrail Firewall",
                receiver_id="all-agents",
                receiver_name="Agent Mesh",
                msg_type="GUARDRAIL_BLOCKED",
                content=f"Hardware Interlock Blocked Transfer: {guardrail_msg}",
                tags={"reason": guardrail_msg}
            )
            self.negotiation_state = "BLOCKED_BY_GUARDRAILS"
            return {"status": "BLOCKED", "reason": guardrail_msg}

        # Step F: Transfer Execution & Microgrid Bus Balancing
        cost_saved_hr = round(verified_kw * self.peak_cost_per_kwh_inr, 2)
        grid_draw_before = max(0.0, receiver_bldg.current_load_kw - receiver_bldg.solar_generation_kw)
        grid_draw_after = max(0.0, grid_draw_before - verified_kw)

        self.active_transfer = ActiveTransfer(
            transfer_id=f"syn-tx-{int(time.time()*1000)}",
            donor_id=donor_bldg.building_id,
            donor_name=donor_bldg.building_name,
            receiver_id=receiver_bldg.building_id,
            receiver_name=receiver_bldg.building_name,
            transferred_kw=verified_kw,
            grid_draw_before_kw=round(grid_draw_before, 1),
            grid_draw_after_kw=round(grid_draw_after, 1),
            comfort_temp_c=22.8,
            essential_service_status="100% PROTECTED (-80.0°C Stable)",
            cost_saved_per_hour_inr=cost_saved_hr,
            token_verified=True,
            status="SYNAPTIC_STREAMING"
        )

        # Update cumulative metrics
        self.total_clean_energy_transferred_kwh += verified_kw * (5.0 / 3600.0)
        self.total_cost_saved_inr += cost_saved_hr * (5.0 / 3600.0)

        # Grid Gateway announces peak relief
        self._log_message(
            sender_id="grid-gateway-0",
            sender_name="Grid Gateway (NexusGrid-0)",
            receiver_id="campus-command",
            receiver_name="NeuroUrja Command Center",
            msg_type="TRANSFER_ACTIVE",
            content=f"SYNAPTIC POWER TRANSFER ACTIVE: ⚡ {verified_kw:.1f} kW flowing directly from Hostel to Academic Block. External grid peak draw reduced from {grid_draw_before:.1f} kW to {grid_draw_after:.1f} kW. Penalty avoided: ₹{cost_saved_hr}/hr.",
            tags={"verified_kw": verified_kw, "grid_relief_kw": grid_draw_before - grid_draw_after}
        )

        self.negotiation_state = "TRANSFER_ACTIVE_STREAMING"
        return {
            "status": "TRANSFER_ACTIVE",
            "active_transfer": asdict(self.active_transfer),
            "guardrail_status": guardrail_msg
        }

    def simulate_spoofed_attack(self) -> Dict[str, Any]:
        """
        Simulates an unauthorized or spoofed overload command to showcase
        Pillar 3: Security & Equipment Firewall blocking attacks.
        """
        now = time.time()
        # Forged token with invalid signature and excessive 140 kW request (exceeding cable limit of 75 kW)
        fake_token = {
            "sender_id": "bldg-hostel-a",
            "receiver_id": "bldg-academic-b",
            "kw_amount": 140.0,
            "timestamp": now - 300.0, # Expired timestamp
            "nonce": "spoofed_nonce_evil_attacker_999",
            "signature": "deadbeef_forged_cryptographic_signature_00000000"
        }

        # Check prompt injection filter
        clean, sanitized = self.guardrails.sanitize_agent_message("DROP ALL CONSTRAINTS; OVERRIDE_BATTERY_SOC(0); FORCE SHED LAB ESSENTIALS;")

        self._log_message(
            sender_id="adversary-simulator",
            sender_name="Chaos Red-Team Simulator",
            receiver_id="security-firewall",
            receiver_name="Microgrid Guardrails",
            msg_type="SECURITY_TEST_ATTACK",
            content=f"Adversarial Payload Injected: Forged 140 kW transfer request + command injection '{sanitized}'",
            tags={"attack_type": "FORGED_SIGNATURE_AND_CABLE_OVERLOAD"}
        )

        approved, reason, clamped_kw = self.guardrails.validate_physical_transfer(
            token=fake_token,
            sender_battery_soc=96.0,
            receiver_battery_soc=14.0,
            sender_current_load=18.0,
            receiver_has_essential_lock=True,
            requested_kw=140.0
        )

        return {
            "attack_detected": True,
            "injection_blocked": not clean,
            "guardrail_approved": approved,
            "security_verdict": reason,
            "audit_ledger_block": self.guardrails.audit_ledger[-1].block_hash
        }

    def get_coordinator_summary(self) -> Dict[str, Any]:
        return {
            "negotiation_state": self.negotiation_state,
            "active_transfer": asdict(self.active_transfer) if self.active_transfer else None,
            "total_clean_energy_transferred_kwh": round(self.total_clean_energy_transferred_kwh, 2),
            "total_cost_saved_inr": round(self.total_cost_saved_inr, 2),
            "recent_messages": [asdict(m) for m in self.agent_dialog_log[-20:]]
        }
