"""
world_state.py
──────────────
SimPy-based world state for the LA Fulfillment Coordination System.

Models:
  - 5 warehouses in Los Angeles with pick-pack capacity (SimPy Resource),
    live queue status, and random disruptions (pick-pack slowdowns).
  - 3 carriers (FedEx, UPS, USPS) with daily cutoff times and
    random shipping delay disruptions.

Disruptions are randomly rolled on each run with varying severity.
"""

import simpy
import random
from datetime import datetime


# ── Simulation clock ───────────────────────────────────────────────
def current_sim_time() -> int:
    """Returns the current real-world time as minutes since midnight."""
    now = datetime.now()
    return now.hour * 60 + now.minute


# ─────────────────────────────────────────────────────────────────
# SHIPPING TIERS
# ─────────────────────────────────────────────────────────────────
SHIPPING_TIERS = {
    "standard": {
        "label":       "Standard Delivery",
        "description": "3-5 business days",
        "services": {
            "FedEx": "FedEx Ground",
            "UPS":   "UPS Ground",
            "USPS":  "USPS Ground",
        },
    },
    "premium": {
        "label":       "Premium Delivery",
        "description": "2 business days",
        "services": {
            "FedEx": "FedEx 2Day",
            "UPS":   "UPS 2nd Day Air",
            "USPS":  "USPS Priority Mail",
        },
    },
    "express": {
        "label":       "Express Delivery",
        "description": "Next business day",
        "services": {
            "FedEx": "FedEx Overnight",
            "UPS":   "UPS Next Day Air",
            # USPS has no overnight service
        },
    },
}


# ─────────────────────────────────────────────────────────────────
# DISRUPTION CONFIGURATION
# ─────────────────────────────────────────────────────────────────
WAREHOUSE_DISRUPTION_CHANCE = 0.35      # 35% chance a warehouse is disrupted
CARRIER_DISRUPTION_CHANCE   = 0.30      # 30% chance a carrier is disrupted

WAREHOUSE_DISRUPTION_SEVERITIES = {
    "minor": {
        "slowdown_pct":  0.20,          # 20% reduction in pick-pack rate
        "label":         "Minor Slowdown",
        "reasons": [
            "Staff shortage on shift",
            "Minor equipment maintenance",
            "Inventory reorganization in progress",
        ],
    },
    "moderate": {
        "slowdown_pct":  0.45,
        "label":         "Moderate Disruption",
        "reasons": [
            "Conveyor belt malfunction",
            "System outage affecting scan stations",
            "High volume backlog from previous shift",
        ],
    },
    "severe": {
        "slowdown_pct":  0.70,
        "label":         "Severe Disruption",
        "reasons": [
            "Power outage affecting warehouse floor",
            "Safety inspection — partial shutdown",
            "Major equipment failure",
        ],
    },
}

CARRIER_DISRUPTION_SEVERITIES = {
    "minor": {
        "delay_days":  1,
        "label":       "Minor Delay",
        "reasons": [
            "High package volume",
            "Sorting facility backlog",
            "Driver shortage in region",
        ],
    },
    "moderate": {
        "delay_days":  2,
        "label":       "Moderate Delay",
        "reasons": [
            "Weather conditions affecting routes",
            "Fuel shortage impacting fleet",
            "Regional hub congestion",
        ],
    },
    "severe": {
        "delay_days":  3,
        "label":       "Severe Delay",
        "reasons": [
            "Major storm disrupting LA routes",
            "Strike action at sorting facility",
            "Critical system outage at carrier hub",
        ],
    },
}


# ─────────────────────────────────────────────────────────────────
# WAREHOUSE DEFINITIONS
# ─────────────────────────────────────────────────────────────────
WAREHOUSE_CONFIGS = {
    "Northridge": {
        "address":      "9301 Tampa Ave, Northridge, CA 91324",
        "lat":           34.2257,
        "lon":          -118.5703,
        "capacity":      5,
        "pick_pack_hr":  120,
        "zone":          "San Fernando Valley",
    },
    "Long Beach": {
        "address":      "2401 E Anaheim St, Long Beach, CA 90804",
        "lat":           33.7701,
        "lon":          -118.1737,
        "capacity":      8,
        "pick_pack_hr":  200,
        "zone":          "South Bay / Port",
    },
    "Ontario": {
        "address":      "3700 E Inland Empire Blvd, Ontario, CA 91764",
        "lat":           34.0633,
        "lon":          -117.5987,
        "capacity":      10,
        "pick_pack_hr":  250,
        "zone":          "Inland Empire",
    },
    "Santa Monica": {
        "address":      "1450 10th St, Santa Monica, CA 90401",
        "lat":           34.0195,
        "lon":          -118.4912,
        "capacity":      3,
        "pick_pack_hr":  80,
        "zone":          "Westside",
    },
    "Monterey Park": {
        "address":      "500 S Atlantic Blvd, Monterey Park, CA 91754",
        "lat":           34.0584,
        "lon":          -118.1220,
        "capacity":      6,
        "pick_pack_hr":  150,
        "zone":          "San Gabriel Valley",
    },
}


# ─────────────────────────────────────────────────────────────────
# CARRIER DEFINITIONS
# ─────────────────────────────────────────────────────────────────
CARRIER_CONFIGS = {
    "FedEx": {
        "cutoff_minutes": 900,
        "cutoff_label":   "3:00 PM",
        "services": [
            {"name": "FedEx Overnight", "days": 1, "cost": 9.99},
            {"name": "FedEx 2Day",      "days": 2, "cost": 5.99},
            {"name": "FedEx Ground",    "days": 3, "cost": 1.99},
        ],
    },
    "UPS": {
        "cutoff_minutes": 960,
        "cutoff_label":   "4:00 PM",
        "services": [
            {"name": "UPS Next Day Air", "days": 1, "cost": 9.99},
            {"name": "UPS 2nd Day Air",  "days": 2, "cost": 5.99},
            {"name": "UPS Ground",       "days": 3, "cost": 1.99},
        ],
    },
    "USPS": {
        "cutoff_minutes": 840,
        "cutoff_label":   "2:00 PM",
        "services": [
            {"name": "USPS Priority Mail", "days": 2, "cost": 9.99},
            {"name": "USPS First Class",   "days": 3, "cost": 5.99},
            {"name": "USPS Ground",        "days": 5, "cost": 1.99},
        ],
    },
}


# ─────────────────────────────────────────────────────────────────
# DISRUPTION ROLLER
# ─────────────────────────────────────────────────────────────────
def roll_warehouse_disruptions() -> dict:
    """Randomly assigns disruptions to warehouses at startup."""
    disruptions = {}
    for name in WAREHOUSE_CONFIGS:
        if random.random() < WAREHOUSE_DISRUPTION_CHANCE:
            severity = random.choice(["minor", "moderate", "severe"])
            cfg      = WAREHOUSE_DISRUPTION_SEVERITIES[severity]
            disruptions[name] = {
                "severity":     severity,
                "label":        cfg["label"],
                "slowdown_pct": cfg["slowdown_pct"],
                "reason":       random.choice(cfg["reasons"]),
            }
    return disruptions


def roll_carrier_disruptions() -> dict:
    """Randomly assigns disruptions to carriers at startup."""
    disruptions = {}
    for name in CARRIER_CONFIGS:
        if random.random() < CARRIER_DISRUPTION_CHANCE:
            severity = random.choice(["minor", "moderate", "severe"])
            cfg      = CARRIER_DISRUPTION_SEVERITIES[severity]
            disruptions[name] = {
                "severity":   severity,
                "label":      cfg["label"],
                "delay_days": cfg["delay_days"],
                "reason":     random.choice(cfg["reasons"]),
            }
    return disruptions


# ─────────────────────────────────────────────────────────────────
# WORLD STATE CLASS
# ─────────────────────────────────────────────────────────────────
class WorldState:
    def __init__(self):
        self.env = simpy.Environment()
        self.warehouses = {}
        self.carriers   = CARRIER_CONFIGS

        # Roll disruptions once at startup
        self.warehouse_disruptions = roll_warehouse_disruptions()
        self.carrier_disruptions   = roll_carrier_disruptions()

        for name, config in WAREHOUSE_CONFIGS.items():
            # Apply slowdown if disrupted
            disruption  = self.warehouse_disruptions.get(name)
            effective_rate = config["pick_pack_hr"]
            if disruption:
                reduction      = disruption["slowdown_pct"]
                effective_rate = round(config["pick_pack_hr"] * (1 - reduction))

            self.warehouses[name] = {
                **config,
                "pick_pack_hr_effective": effective_rate,
                "resource": simpy.Resource(self.env, capacity=config["capacity"]),
                "name": name,
            }

    # ── Warehouse queries ─────────────────────────────────────────
    def get_warehouse_status(self, name: str) -> dict:
        wh = self.warehouses.get(name)
        if not wh:
            return {"error": f"Warehouse '{name}' not found."}

        resource     = wh["resource"]
        in_use       = resource.count
        capacity     = resource.capacity
        queue_length = len(resource.queue)
        available    = capacity - in_use

        if in_use == 0:
            queue_status = "FREE — no active orders"
        elif available > 0:
            queue_status = f"BUSY — {in_use}/{capacity} slots in use, {available} slot(s) available"
        else:
            queue_status = f"AT CAPACITY — all {capacity} slots in use, {queue_length} order(s) waiting"

        disruption = self.warehouse_disruptions.get(name)

        return {
            "name":                name,
            "address":             wh["address"],
            "zone":                wh["zone"],
            "capacity":            capacity,
            "slots_in_use":        in_use,
            "slots_available":     available,
            "queue_length":        queue_length,
            "queue_status":        queue_status,
            "pick_pack_hr":        wh["pick_pack_hr"],
            "pick_pack_hr_effective": wh["pick_pack_hr_effective"],
            "disruption":          disruption,
        }

    def get_all_warehouse_statuses(self) -> list:
        return [self.get_warehouse_status(name) for name in self.warehouses]

    # ── Carrier queries ───────────────────────────────────────────
    def get_carrier_status(self, carrier_name: str) -> dict:
        carrier = self.carriers.get(carrier_name)
        if not carrier:
            return {"error": f"Carrier '{carrier_name}' not found."}

        now_minutes = current_sim_time()
        cutoff      = carrier["cutoff_minutes"]
        accepting   = now_minutes < cutoff

        minutes_remaining = cutoff - now_minutes if accepting else 0
        hours_rem = minutes_remaining // 60
        mins_rem  = minutes_remaining % 60

        disruption = self.carrier_disruptions.get(carrier_name)

        # Apply delay to services if disrupted
        services = []
        for svc in carrier["services"]:
            effective_days = svc["days"] + (disruption["delay_days"] if disruption else 0)
            services.append({**svc, "effective_days": effective_days})

        return {
            "carrier":           carrier_name,
            "cutoff":            carrier["cutoff_label"],
            "accepting_orders":  accepting,
            "minutes_remaining": minutes_remaining,
            "time_remaining":    f"{hours_rem}h {mins_rem}m" if accepting else "CLOSED",
            "services":          services,
            "disruption":        disruption,
        }

    def get_all_carrier_statuses(self) -> list:
        return [self.get_carrier_status(name) for name in self.carriers]

    # ── Processing time estimate ──────────────────────────────────
    def simulate_order_processing(self, warehouse_name: str, units: int):
        wh = self.warehouses.get(warehouse_name)
        if not wh:
            return None
        effective_rate = wh["pick_pack_hr_effective"]
        return round((units / effective_rate) * 60, 2)

    # ── Shipping tier queries ─────────────────────────────────────
    def get_shipping_tier(self, tier_key: str) -> dict:
        return SHIPPING_TIERS.get(tier_key.lower())

    def get_all_shipping_tiers(self) -> dict:
        return SHIPPING_TIERS

    # ── Disruption summary ────────────────────────────────────────
    def get_all_disruptions(self) -> dict:
        return {
            "warehouse_disruptions": self.warehouse_disruptions,
            "carrier_disruptions":   self.carrier_disruptions,
        }


# ── Singleton ─────────────────────────────────────────────────────
world = WorldState()