from crewai.tools import tool
from world_state import world


@tool("Get Active Disruptions")
def get_active_disruptions() -> str:
    """
    Returns all currently active disruptions across warehouses and carriers.
    Always call this FIRST before making any fulfillment or shipping decisions.
    No input needed.
    """
    data = world.get_all_disruptions()
    wh_disruptions  = data["warehouse_disruptions"]
    car_disruptions = data["carrier_disruptions"]

    if not wh_disruptions and not car_disruptions:
        return "✅ No active disruptions — all warehouses and carriers operating normally."

    output = "⚠️  ACTIVE DISRUPTIONS THIS RUN:\n"

    if wh_disruptions:
        output += "\n  🏭 Warehouse Disruptions:\n"
        for name, d in wh_disruptions.items():
            output += (
                f"    ❌ {name} — {d['label']} (severity: {d['severity']})\n"
                f"       Reason      : {d['reason']}\n"
                f"       Pick-pack slowdown: {int(d['slowdown_pct'] * 100)}% reduction in throughput\n"
            )
    else:
        output += "\n  🏭 Warehouse Disruptions: None\n"

    if car_disruptions:
        output += "\n  🚚 Carrier Disruptions:\n"
        for name, d in car_disruptions.items():
            output += (
                f"    ❌ {name} — {d['label']} (severity: {d['severity']})\n"
                f"       Reason      : {d['reason']}\n"
                f"       Added delay : +{d['delay_days']} day(s) to all services\n"
            )
    else:
        output += "\n  🚚 Carrier Disruptions: None\n"

    return output


@tool("Get Warehouse Queue Status")
def get_warehouse_queue_status(warehouse_name: str) -> str:
    """
    Returns the live operational status of a specific warehouse,
    including any active disruption and its effect on pick-pack rate.
    Input: warehouse name (string).
    """
    status = world.get_warehouse_status(warehouse_name)

    if "error" in status:
        return status["error"]

    disruption = status["disruption"]
    if disruption:
        disruption_str = (
            f"\n  ⚠️  DISRUPTION ACTIVE:\n"
            f"     Severity    : {disruption['label']}\n"
            f"     Reason      : {disruption['reason']}\n"
            f"     Slowdown    : {int(disruption['slowdown_pct'] * 100)}% reduction\n"
            f"     Effective Rate: {status['pick_pack_hr_effective']} units/hr "
            f"(normal: {status['pick_pack_hr']} units/hr)\n"
        )
    else:
        disruption_str = "\n  ✅ No disruptions — operating at full capacity.\n"

    return (
        f"Warehouse: {status['name']}\n"
        f"  Address        : {status['address']}\n"
        f"  Zone           : {status['zone']}\n"
        f"  Queue Status   : {status['queue_status']}\n"
        f"  Slots In Use   : {status['slots_in_use']} / {status['capacity']}\n"
        f"  Slots Available: {status['slots_available']}\n"
        f"  Pick-Pack Rate : {status['pick_pack_hr_effective']} units/hr"
        f"{disruption_str}"
    )


@tool("Get All Warehouse Statuses")
def get_all_warehouse_statuses() -> str:
    """
    Returns the live status of ALL warehouses including disruptions.
    Use this to compare warehouses before routing an order.
    No input needed.
    """
    statuses = world.get_all_warehouse_statuses()
    output = "🏭 LA Warehouse Network — Live Status:\n\n"

    for s in statuses:
        disruption = s["disruption"]
        if disruption:
            disruption_tag = f"⚠️  {disruption['label']} (+{int(disruption['slowdown_pct']*100)}% slower)"
        else:
            disruption_tag = "✅ No disruption"

        output += f"  📦 {s['name']} ({s['zone']})\n"
        output += f"     Queue      : {s['queue_status']}\n"
        output += f"     Slots      : {s['slots_in_use']}/{s['capacity']} in use\n"
        output += f"     Pick-Pack  : {s['pick_pack_hr_effective']} units/hr\n"
        output += f"     Disruption : {disruption_tag}\n\n"

    return output


@tool("Estimate Order Processing Time")
def estimate_order_processing_time(warehouse_name: str, units: int) -> str:
    """
    Estimates how long a warehouse will take to pick and pack an order,
    accounting for any active disruptions slowing down the pick-pack rate.
    Input: warehouse name and number of units.
    """
    processing_min = world.simulate_order_processing(warehouse_name, int(units))

    if processing_min is None:
        return f"Warehouse '{warehouse_name}' not found."

    status = world.get_warehouse_status(warehouse_name)
    hours  = int(processing_min // 60)
    mins   = int(processing_min % 60)
    time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"

    disruption = status["disruption"]
    if disruption:
        disruption_note = (
            f"  ⚠️  Disruption active: {disruption['label']} — "
            f"rate reduced by {int(disruption['slowdown_pct']*100)}%\n"
            f"     Normal rate : {status['pick_pack_hr']} units/hr\n"
            f"     Actual rate : {status['pick_pack_hr_effective']} units/hr\n"
        )
    else:
        disruption_note = "  ✅ No disruption — running at full pick-pack rate.\n"

    slot_note = (
        "  ✅ Slot available — can begin immediately.\n"
        if status["slots_available"] > 0
        else "  ⚠️  At capacity — expect a queue delay before processing starts.\n"
    )

    return (
        f"Processing estimate for {units} unit(s) at '{warehouse_name}':\n"
        f"  Estimated Time : {time_str}\n"
        f"  Queue Status   : {status['queue_status']}\n"
        f"{disruption_note}"
        f"{slot_note}"
    )


@tool("Check Carrier Cutoff")
def check_carrier_cutoff(carrier_name: str) -> str:
    """
    Checks whether a carrier is still accepting orders and whether it has
    an active disruption adding delays to delivery times.
    Input: carrier name — 'FedEx', 'UPS', or 'USPS'.
    """
    status = world.get_carrier_status(carrier_name)

    if "error" in status:
        return status["error"]

    accepting_str = (
        f"✅ ACCEPTING — {status['time_remaining']} until cutoff"
        if status["accepting_orders"]
        else "❌ CLOSED — cutoff passed, next pickup tomorrow"
    )

    disruption = status["disruption"]
    if disruption:
        disruption_str = (
            f"\n  ⚠️  DISRUPTION ACTIVE:\n"
            f"     Severity  : {disruption['label']}\n"
            f"     Reason    : {disruption['reason']}\n"
            f"     Added delay: +{disruption['delay_days']} day(s) to all services\n"
        )
    else:
        disruption_str = "\n  ✅ No disruption — all services running on schedule.\n"

    output = (
        f"Carrier: {status['carrier']}\n"
        f"  Cutoff  : {status['cutoff']}\n"
        f"  Status  : {accepting_str}"
        f"{disruption_str}"
        f"  Services (effective delivery days):\n"
    )
    for svc in status["services"]:
        delay_note = f" (+{disruption['delay_days']}d disruption)" if disruption else ""
        output += (
            f"    - {svc['name']}: {svc['effective_days']} day(s){delay_note} | ${svc['cost']}\n"
        )

    return output


@tool("Check All Carrier Cutoffs")
def check_all_carrier_cutoffs() -> str:
    """
    Checks cutoff status AND disruptions for ALL carriers right now.
    Use this before recommending any carrier.
    No input needed.
    """
    statuses = world.get_all_carrier_statuses()
    output = "🚚 Carrier Status — Right Now:\n\n"

    for s in statuses:
        status_str = (
            f"✅ OPEN — closes at {s['cutoff']} ({s['time_remaining']} left)"
            if s["accepting_orders"]
            else f"❌ CLOSED — cutoff was {s['cutoff']}"
        )

        disruption = s["disruption"]
        if disruption:
            disruption_str = (
                f"⚠️  {disruption['label']}: {disruption['reason']} "
                f"(+{disruption['delay_days']}d on all services)"
            )
        else:
            disruption_str = "✅ No disruption"

        output += f"  {s['carrier']}\n"
        output += f"    Cutoff     : {s['cutoff']}\n"
        output += f"    Status     : {status_str}\n"
        output += f"    Disruption : {disruption_str}\n"
        output += f"    Services   :\n"
        for svc in s["services"]:
            delay_note = f" (+{disruption['delay_days']}d)" if disruption else ""
            output += (
                f"      - {svc['name']}: {svc['effective_days']} day(s){delay_note}"
                f" | ${svc['cost']}\n"
            )
        output += "\n"

    return output


@tool("Check Carriers For Tier")
def check_carriers_for_tier(tier: str) -> str:
    """
    Checks carrier availability, cutoffs, and disruptions for a specific
    delivery tier: 'standard', 'premium', or 'express'.
    Only returns the services that match the requested tier.
    Input: tier name — 'standard', 'premium', or 'express'.
    """
    tier_data = world.get_shipping_tier(tier)
    if not tier_data:
        return f"Unknown tier '{tier}'. Choose from: standard, premium, express."

    output = (
        f"🚚 Carrier Options for {tier_data['label']} ({tier_data['description']}):\n\n"
    )

    for carrier_name, service_name in tier_data["services"].items():
        status = world.get_carrier_status(carrier_name)

        accepting_str = (
            f"✅ OPEN — {status['time_remaining']} until cutoff"
            if status["accepting_orders"]
            else f"❌ CLOSED — cutoff was {status['cutoff']}"
        )

        disruption = status["disruption"]

        # Find the matching service and its effective days
        matched_service = next(
            (s for s in status["services"] if s["name"] == service_name), None
        )

        if not matched_service:
            continue

        delay_note = (
            f" (+{disruption['delay_days']}d disruption)" if disruption else ""
        )
        effective_days = matched_service["effective_days"]

        output += f"  {carrier_name} — {service_name}\n"
        output += f"    Cutoff     : {status['cutoff']}\n"
        output += f"    Status     : {accepting_str}\n"
        output += f"    Delivery   : {effective_days} day(s){delay_note}\n"
        output += f"    Cost       : ${matched_service['cost']}\n"

        if disruption:
            output += (
                f"    ⚠️  Disruption: {disruption['label']} — {disruption['reason']}\n"
            )
        else:
            output += f"    ✅ No disruption\n"
        output += "\n"

    return output