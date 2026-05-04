'''
from crewai import Task
from agents import (
    order_intake_agent,
    inventory_agent,
    capacity_agent,
    shipping_agent,
    coordinator_agent,
)


def build_tasks(order: dict) -> list[Task]:
    destination = order["destination"]
    items       = order["items"]

    items_summary = "\n".join(
        f"    - {item['product']}: {item['quantity']} unit(s)" for item in items
    )
    items_tool_format = ",".join(
        f"{item['product']}:{item['quantity']}" for item in items
    )
    total_units = sum(item["quantity"] for item in items)

    # ─────────────────────────────────────────────
    # Task 1: Order Intake
    # ─────────────────────────────────────────────
    intake_task = Task(
        description=(
            f"A new customer order has been received:\n"
            f"  Items Ordered:\n{items_summary}\n"
            f"  Destination: {destination}\n\n"
            "Validate and structure this order. List all available warehouse locations "
            "so downstream agents know which locations to evaluate. "
            "Confirm all order details are complete and ready for processing."
        ),
        expected_output=(
            "A structured order summary listing each product, quantity requested, "
            "destination, and all known warehouse locations."
        ),
        agent=order_intake_agent,
    )

    # ─────────────────────────────────────────────
    # Task 2: Inventory Check
    # ─────────────────────────────────────────────
    inventory_task = Task(
        description=(
            f"Check inventory levels for each product across all warehouse locations:\n"
            f"{items_summary}\n\n"
            "For each product, identify which locations have sufficient stock "
            "and which are out of stock or understocked."
        ),
        expected_output=(
            "A per-product inventory report showing stock levels at each location, "
            "highlighting which locations can fulfill each item's quantity requirement."
        ),
        agent=inventory_agent,
        context=[intake_task],
    )

    # ─────────────────────────────────────────────
    # Task 3: Capacity, World State & Disruption Check
    # ─────────────────────────────────────────────
    capacity_task = Task(
        description=(
            f"Determine the optimal fulfillment strategy for this order:\n"
            f"{items_summary}\n\n"
            "Follow these steps in order:\n\n"
            "Step 1 — Call 'Get Active Disruptions' to see which warehouses are disrupted.\n\n"
            f"Step 2 — Call 'Find Best Fulfillment Plan For Order' with input: '{items_tool_format}' "
            "to find which warehouse(s) have the inventory.\n\n"
            "Step 3 — Call 'Get All Warehouse Statuses' to check live queue and pick-pack rates "
            "for all warehouses, including disruption-adjusted rates.\n\n"
            f"Step 4 — For the top candidate warehouse(s), call 'Estimate Order Processing Time' "
            f"with {total_units} total units.\n\n"
            "Decision rules:\n"
            "  - PREFER warehouses with inventory, available slots, AND no disruption.\n"
            "  - If a warehouse has inventory but is disrupted, consider routing to an "
            "alternate warehouse if one exists with sufficient stock.\n"
            "  - If no better alternative exists, use the disrupted warehouse but flag it.\n"
            "  - If no single warehouse can fulfill all items, plan a split shipment.\n"
        ),
        expected_output=(
            "A fulfillment recommendation stating:\n"
            "- Any active warehouse disruptions and their impact\n"
            "- SINGLE or SPLIT shipment decision\n"
            "- For each warehouse: name, inventory, queue status, disruption status, "
            "effective pick-pack rate, and estimated processing time\n"
            "- Whether re-routing was applied due to a disruption\n"
            "- Final recommended warehouse(s) with justification"
        ),
        agent=capacity_agent,
        context=[intake_task, inventory_task],
    )

    # ─────────────────────────────────────────────
    # Task 4: Shipping & Carrier Disruption Check
    # ─────────────────────────────────────────────
    tier         = order.get("tier", "standard")
    tier_labels  = {
        "standard": "Standard Delivery (3-5 days)",
        "premium":  "Premium Delivery (2 days)",
        "express":  "Express Delivery (Next day)",
    }
    tier_label = tier_labels.get(tier, tier)

    shipping_task = Task(
        description=(
            f"Evaluate shipping options based on the fulfillment plan.\n"
            f"Customer destination : {destination}\n"
            f"Requested tier       : {tier_label}\n\n"
            "Follow these steps in order:\n\n"
            f"Step 1 — Call 'Check Carriers For Tier' with input '{tier}' to get only "
            "the carrier services that match the customer's requested delivery tier.\n\n"
            "Step 2 — For each carrier in the tier:\n"
            "  - If CLOSED: flag it, do not recommend for today.\n"
            "  - If OPEN but DISRUPTED: include it but note the added delay days.\n"
            "  - If OPEN and NO disruption: recommend normally.\n\n"
            "Step 3 — Re-route preference: if the preferred carrier for this tier is "
            "disrupted or closed, recommend the next best open carrier within the same tier.\n\n"
            "Step 4 — For split shipments, evaluate each warehouse leg separately.\n\n"
            "Note: Do NOT recommend services outside the customer's requested tier."
        ),
        expected_output=(
            f"Carrier evaluation for the '{tier}' tier including:\n"
            "- Which tier-matched carriers are open vs closed\n"
            "- Which have disruptions and effective delivery days\n"
            "- Recommended carrier per shipment leg (with re-route note if applicable)\n"
            "- Cost and effective delivery days per service"
        ),
        agent=shipping_agent,
        context=[capacity_task],
    )

    # ─────────────────────────────────────────────
    # Task 5: Coordinator — Final Plan
    # ─────────────────────────────────────────────
    coordinator_task = Task(
        description=(
            "Synthesize all findings into the final fulfillment plan:\n"
            f"  Items:\n{items_summary}\n"
            f"  Destination      : {destination}\n"
            f"  Delivery Tier    : {tier_label}\n\n"
            "The plan must include:\n"
            "  1. A DISRUPTION SUMMARY — list any active warehouse or carrier disruptions\n"
            "  2. Shipment type: SINGLE or SPLIT\n"
            "  3. Per shipment leg:\n"
            "       - Warehouse name, zone, and address\n"
            "       - Products and quantities\n"
            "       - Queue status and estimated pick-pack time\n"
            "       - Any warehouse disruption and its impact\n"
            "       - Selected carrier, service, effective delivery days, and cost\n"
            "       - Any carrier disruption and added delay\n"
            "       - Whether re-routing was applied\n"
            "       - Estimated arrival\n"
            "  4. If SPLIT: notify customer to expect multiple deliveries\n"
            "  5. Any unfulfillable items and why"
        ),
        expected_output=(
            "A complete fulfillment plan including:\n"
            "- Disruption summary at the top\n"
            "- Shipment type (single or split)\n"
            "- Per leg: warehouse, products, disruption status, processing time, "
            "carrier, cost, effective ETA\n"
            "- Re-routing notes where applicable\n"
            "- Unfulfillable items if any"
        ),
        agent=coordinator_agent,
        context=[intake_task, inventory_task, capacity_task, shipping_task],
    )

    return [intake_task, inventory_task, capacity_task, shipping_task, coordinator_task]

'''

from crewai import Task
from agents import (
    order_intake_agent,
    inventory_agent,
    capacity_agent,
    shipping_agent,
    coordinator_agent,
)


def build_tasks(order: dict) -> list[Task]:
    destination = order["destination"]
    items       = order["items"]

    items_summary = "\n".join(
        f"    - {item['product']}: {item['quantity']} unit(s)" for item in items
    )
    items_tool_format = ",".join(
        f"{item['product']}:{item['quantity']}" for item in items
    )
    total_units = sum(item["quantity"] for item in items)

    # ─────────────────────────────────────────────
    # Task 1: Order Intake
    # ─────────────────────────────────────────────
    intake_task = Task(
        description=(
            f"A new customer order has been received:\n"
            f"  Items Ordered:\n{items_summary}\n"
            f"  Destination: {destination}\n\n"
            "Validate and structure this order. List all available warehouse locations "
            "so downstream agents know which locations to evaluate. "
            "Confirm all order details are complete and ready for processing."
        ),
        expected_output=(
            "A structured order summary listing each product, quantity requested, "
            "destination, and all known warehouse locations."
        ),
        agent=order_intake_agent,
    )

    # ─────────────────────────────────────────────
    # Task 2: Inventory Check
    # ─────────────────────────────────────────────
    inventory_task = Task(
        description=(
            f"Check inventory levels for each product across all warehouse locations:\n"
            f"{items_summary}\n\n"
            "For each product, identify which locations have sufficient stock "
            "and which are out of stock or understocked."
        ),
        expected_output=(
            "A per-product inventory report showing stock levels at each location, "
            "highlighting which locations can fulfill each item's quantity requirement."
        ),
        agent=inventory_agent,
        context=[intake_task],
    )

    # ─────────────────────────────────────────────
    # Task 3: Capacity, World State & Disruption Check
    # ─────────────────────────────────────────────
    capacity_task = Task(
        description=(
            f"Determine the optimal fulfillment strategy for this order:\n"
            f"{items_summary}\n\n"
            "Follow these steps in order:\n\n"
            "Step 1 — Call 'Get Active Disruptions' to see which warehouses are disrupted.\n\n"
            f"Step 2 — Call 'Find Best Fulfillment Plan For Order' with input: '{items_tool_format}' "
            "to find which warehouse(s) have the inventory.\n\n"
            "Step 3 — Call 'Get All Warehouse Statuses' to check live queue and pick-pack rates "
            "for all warehouses, including disruption-adjusted rates.\n\n"
            f"Step 4 — For the top candidate warehouse(s), call 'Estimate Order Processing Time' "
            f"with {total_units} total units.\n\n"
            "Decision rules:\n"
            "  - PREFER warehouses with inventory, available slots, AND no disruption.\n"
            "  - If a warehouse has inventory but is disrupted, consider routing to an "
            "alternate warehouse if one exists with sufficient stock.\n"
            "  - If no better alternative exists, use the disrupted warehouse but flag it.\n"
            "  - If no single warehouse can fulfill all items, plan a split shipment.\n"
        ),
        expected_output=(
            "A fulfillment recommendation stating:\n"
            "- Any active warehouse disruptions and their impact\n"
            "- SINGLE or SPLIT shipment decision\n"
            "- For each warehouse: name, inventory, queue status, disruption status, "
            "effective pick-pack rate, and estimated processing time\n"
            "- Whether re-routing was applied due to a disruption\n"
            "- Final recommended warehouse(s) with justification"
        ),
        agent=capacity_agent,
        context=[intake_task, inventory_task],
    )

    # ─────────────────────────────────────────────
    # Task 4: Shipping & Carrier Disruption Check
    # ─────────────────────────────────────────────
    tier         = order.get("tier", "standard")
    tier_labels  = {
        "standard": "Standard Delivery (3-5 days)",
        "premium":  "Premium Delivery (2 days)",
        "express":  "Express Delivery (Next day)",
    }
    tier_label = tier_labels.get(tier, tier)

    shipping_task = Task(
        description=(
            f"Evaluate shipping options based on the fulfillment plan.\n"
            f"Customer destination : {destination}\n"
            f"Requested tier       : {tier_label}\n\n"
            "Follow these steps in order:\n\n"
            f"Step 1 — Call 'Check Carriers For Tier' with input '{tier}' to get only "
            "the carrier services that match the customer's requested delivery tier.\n\n"
            "Step 2 — For each carrier in the tier:\n"
            "  - If CLOSED: flag it, do not recommend for today.\n"
            "  - If OPEN but DISRUPTED: include it but note the added delay days.\n"
            "  - If OPEN and NO disruption: recommend normally.\n\n"
            "Step 3 — Re-route preference: if the preferred carrier for this tier is "
            "disrupted or closed, recommend the next best open carrier within the same tier.\n\n"
            "Step 4 — For split shipments, evaluate each warehouse leg separately.\n\n"
            "Note: Do NOT recommend services outside the customer's requested tier."
        ),
        expected_output=(
            f"Carrier evaluation for the '{tier}' tier including:\n"
            "- Which tier-matched carriers are open vs closed\n"
            "- Which have disruptions and effective delivery days\n"
            "- Recommended carrier per shipment leg (with re-route note if applicable)\n"
            "- Cost and effective delivery days per service"
        ),
        agent=shipping_agent,
        context=[capacity_task],
    )

    # ─────────────────────────────────────────────
    # Task 5: Coordinator — Final Plan
    # ─────────────────────────────────────────────
    coordinator_task = Task(
        description=(
            "Synthesize all findings into the final fulfillment plan:\n"
            f"  Items:\n{items_summary}\n"
            f"  Destination      : {destination}\n"
            f"  Delivery Tier    : {tier_label}\n\n"
            "The plan must include:\n"
            "  1. A DISRUPTION SUMMARY — list any active warehouse or carrier disruptions\n"
            "  2. Shipment type: SINGLE or SPLIT\n"
            "  3. Per shipment leg:\n"
            "       - Warehouse name, zone, and address\n"
            "       - Products and quantities\n"
            "       - Queue status and estimated pick-pack time\n"
            "       - Any warehouse disruption and its impact\n"
            "       - Selected carrier, service, effective delivery days, and cost\n"
            "       - Any carrier disruption and added delay\n"
            "       - Whether re-routing was applied\n"
            "       - Estimated arrival\n"
            "  4. If SPLIT: notify customer to expect multiple deliveries\n"
            "  5. Any unfulfillable items and why\n\n"
            "FORMAT RULES — follow these exactly:\n"
            "  - Use the section headers and dividers shown in the expected output\n"
            "  - Each section must be clearly separated with a divider line of dashes\n"
            "  - Use emoji indicators: ✅ for good, ⚠️ for warnings, ❌ for problems\n"
            "  - All labels must be left-aligned and values right of a colon\n"
            "  - Do not use markdown, asterisks, or bullet points\n"
            "  - Numbers must include units (days, units, hrs, $)\n"
            "  - Keep each line under 55 characters where possible"
        ),
        expected_output=(
            "Output must follow this exact structure and style:\n\n"
            "══════════════════════════════════════════════════\n"
            "  FULFILLMENT PLAN\n"
            "══════════════════════════════════════════════════\n"
            "  Order Destination : <location>\n"
            "  Delivery Tier     : <tier label>\n"
            "  Shipment Type     : SINGLE SHIPMENT or SPLIT SHIPMENT\n\n"
            "──────────────────────────────────────────────────\n"
            "  DISRUPTION SUMMARY\n"
            "──────────────────────────────────────────────────\n"
            "  Warehouses  : ✅ None  or  ⚠️ <name> — <reason>\n"
            "  Carriers    : ✅ None  or  ⚠️ <name> — <reason>\n\n"
            "──────────────────────────────────────────────────\n"
            "  SHIPMENT 1  (or SHIPMENT 2 for split)\n"
            "──────────────────────────────────────────────────\n"
            "  Warehouse     : <name>\n"
            "  Queue Status  : FREE / BUSY / AT CAPACITY\n"
            "  Processing    : <X> min  (at <N> units/hr)\n"
            "  Disruption    : ✅ None  or  ⚠️ <label> — <impact>\n\n"
            "  Items Shipping:\n"
            "    - <Product> x<qty>\n\n"
            "  Carrier       : <carrier name>\n"
            "  Service       : <service name>\n"
            "  Shipping Cost : $<amount>\n"
            "  Delivery Time : <N> day(s)\n"
            "  Disruption    : ✅ None  or  ⚠️ +<N>d — <reason>\n"
            "  Re-routed     : Yes / No\n"
            "  Est. Arrival  : <N> business day(s) from today\n\n"
            "──────────────────────────────────────────────────\n"
            "  NOTES\n"
            "──────────────────────────────────────────────────\n"
            "  <Any split shipment notices, unfulfillable items,\n"
            "   or important caveats go here. If none, write\n"
            "   'No additional notes.'>\n"
            "══════════════════════════════════════════════════"
        ),
        agent=coordinator_agent,
        context=[intake_task, inventory_task, capacity_task, shipping_task],
    )

    return [intake_task, inventory_task, capacity_task, shipping_task, coordinator_task]