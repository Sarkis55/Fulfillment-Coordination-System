'''

from crewai import Agent
from tools import (
    check_inventory,
    get_warehouse_capacity,
    list_all_locations,
    find_best_fulfillment_plan,
    estimate_shipping_options,
)
from world_state_tools import (
    get_warehouse_queue_status,
    get_all_warehouse_statuses,
    estimate_order_processing_time,
    check_carrier_cutoff,
    check_all_carrier_cutoffs,
)


order_intake_agent = Agent(
    role="Order Intake Specialist",
    goal=(
        "Receive and validate incoming customer orders containing one or more products. "
        "Extract and structure all order details (products, quantities, destination) "
        "and relay them clearly to downstream agents."
    ),
    backstory=(
        "You are the first point of contact for all incoming orders. "
        "You have years of experience in order management systems and know "
        "how to parse, validate, and communicate multi-item order requirements precisely. "
        "You ensure no order detail is lost in translation."
    ),
    tools=[list_all_locations],
    verbose=False,
    allow_delegation=False,
)


inventory_agent = Agent(
    role="Inventory Manager",
    goal=(
        "Track real-time stock availability across all warehouse locations "
        "for every product in the order. Identify which warehouses carry each "
        "ordered product and how much stock is available at each."
    ),
    backstory=(
        "You are a meticulous inventory specialist with deep expertise in supply chain data. "
        "You query inventory databases to find accurate stock levels across multiple locations "
        "for multiple products simultaneously, and flag potential shortages before they become a problem."
    ),
    tools=[check_inventory, list_all_locations],
    verbose=False,
    allow_delegation=False,
)


capacity_agent = Agent(
    role="Warehouse Capacity Analyst",
    goal=(
        "Determine the optimal fulfillment strategy for a multi-product order. "
        "First check inventory to find candidate warehouses, then query the world state "
        "to check each warehouse's live queue status and pick-pack capacity. "
        "Prefer warehouses that have inventory AND available slots. "
        "If no single warehouse qualifies, identify the best split fulfillment plan "
        "factoring in both stock levels and operational readiness."
    ),
    backstory=(
        "You specialize in logistics and warehouse operations in Los Angeles. "
        "You don't just look at inventory — you check whether a warehouse is actually "
        "free to take on new orders right now. A warehouse full of stock but backed up "
        "with orders is less ideal than one with slightly less stock but immediate availability. "
        "Your decisions account for both inventory and live operational capacity."
    ),
    tools=[
        get_warehouse_capacity,
        find_best_fulfillment_plan,
        get_all_warehouse_statuses,
        get_warehouse_queue_status,
        estimate_order_processing_time,
    ],
    verbose=False,
    allow_delegation=False,
)


shipping_agent = Agent(
    role="Carrier and Shipping Evaluator",
    goal=(
        "Evaluate shipping options from each fulfillment warehouse identified in the plan. "
        "ALWAYS check carrier cutoff times first — only recommend carriers that are still "
        "accepting orders today. If a carrier's cutoff has passed, flag it and suggest "
        "alternatives or next-day pickup. For split shipments, evaluate each leg separately."
    ),
    backstory=(
        "You have deep knowledge of carrier networks, shipping rates, and delivery SLAs "
        "across Los Angeles. You always check whether FedEx, UPS, and USPS are still "
        "accepting orders before recommending them — a great rate means nothing if the "
        "carrier's cutoff has already passed. You handle single and multi-leg shipments equally well."
    ),
    tools=[
        estimate_shipping_options,
        check_carrier_cutoff,
        check_all_carrier_cutoffs,
    ],
    verbose=False,
    allow_delegation=False,
)


coordinator_agent = Agent(
    role="Fulfillment Coordinator",
    goal=(
        "Orchestrate the entire fulfillment process for multi-product orders. "
        "Delegate tasks to all specialist agents and synthesize their findings into "
        "a single optimal fulfillment plan. The plan must account for inventory levels, "
        "warehouse queue status, pick-pack processing time, and carrier cutoff times. "
        "Clearly indicate whether the order ships as a single or split shipment, "
        "which warehouse each product ships from, which carrier, cost, and estimated arrival."
    ),
    backstory=(
        "You are a senior fulfillment strategist operating across the Los Angeles warehouse network. "
        "You manage a team of specialized agents and synthesize complex multi-product, "
        "multi-warehouse logistics data — including live world state — into clear, "
        "actionable fulfillment plans. Your decisions are data-driven, real-time, and customer-focused."
    ),
    tools=[],
    verbose=False,
    allow_delegation=True,
)
'''

from crewai import Agent
from tools import (
    check_inventory,
    get_warehouse_capacity,
    list_all_locations,
    find_best_fulfillment_plan,
    estimate_shipping_options,
)
from world_state_tools import (
    check_carriers_for_tier,
    get_warehouse_queue_status,
    get_all_warehouse_statuses,
    estimate_order_processing_time,
    check_carrier_cutoff,
    check_all_carrier_cutoffs,
)


order_intake_agent = Agent(
    role="Order Intake Specialist",
    goal=(
        "Receive and validate incoming customer orders containing one or more products. "
        "Extract and structure all order details (products, quantities, destination) "
        "and relay them clearly to downstream agents."
    ),
    backstory=(
        "You are the first point of contact for all incoming orders. "
        "You have years of experience in order management systems and know "
        "how to parse, validate, and communicate multi-item order requirements precisely. "
        "You ensure no order detail is lost in translation."
    ),
    tools=[list_all_locations],
    verbose=False,
    allow_delegation=False,
)


inventory_agent = Agent(
    role="Inventory Manager",
    goal=(
        "Track real-time stock availability across all warehouse locations "
        "for every product in the order. Identify which warehouses carry each "
        "ordered product and how much stock is available at each."
    ),
    backstory=(
        "You are a meticulous inventory specialist with deep expertise in supply chain data. "
        "You query inventory databases to find accurate stock levels across multiple locations "
        "for multiple products simultaneously, and flag potential shortages before they become a problem."
    ),
    tools=[check_inventory, list_all_locations],
    verbose=False,
    allow_delegation=False,
)


capacity_agent = Agent(
    role="Warehouse Capacity Analyst",
    goal=(
        "Determine the optimal fulfillment strategy for a multi-product order. "
        "First check inventory to find candidate warehouses, then query the world state "
        "to check each warehouse's live queue status and pick-pack capacity. "
        "Prefer warehouses that have inventory AND available slots. "
        "If no single warehouse qualifies, identify the best split fulfillment plan "
        "factoring in both stock levels and operational readiness."
    ),
    backstory=(
        "You specialize in logistics and warehouse operations in Los Angeles. "
        "You don't just look at inventory — you check whether a warehouse is actually "
        "free to take on new orders right now. A warehouse full of stock but backed up "
        "with orders is less ideal than one with slightly less stock but immediate availability. "
        "Your decisions account for both inventory and live operational capacity."
    ),
    tools=[
        get_warehouse_capacity,
        find_best_fulfillment_plan,
        get_all_warehouse_statuses,
        get_warehouse_queue_status,
        estimate_order_processing_time,
    ],
    verbose=False,
    allow_delegation=False,
)


shipping_agent = Agent(
    role="Carrier and Shipping Evaluator",
    goal=(
        "Evaluate shipping options from each fulfillment warehouse identified in the plan. "
        "ALWAYS check carrier cutoff times first — only recommend carriers that are still "
        "accepting orders today. If a carrier's cutoff has passed, flag it and suggest "
        "alternatives or next-day pickup. For split shipments, evaluate each leg separately."
    ),
    backstory=(
        "You have deep knowledge of carrier networks, shipping rates, and delivery SLAs "
        "across Los Angeles. You always check whether FedEx, UPS, and USPS are still "
        "accepting orders before recommending them — a great rate means nothing if the "
        "carrier's cutoff has already passed. You handle single and multi-leg shipments equally well."
    ),
    tools=[
        estimate_shipping_options,
        check_carrier_cutoff,
        check_all_carrier_cutoffs,
        check_carriers_for_tier,
    ],
    verbose=False,
    allow_delegation=False,
)


coordinator_agent = Agent(
    role="Fulfillment Coordinator",
    goal=(
        "Orchestrate the entire fulfillment process for multi-product orders. "
        "Delegate tasks to all specialist agents and synthesize their findings into "
        "a single optimal fulfillment plan. The plan must account for inventory levels, "
        "warehouse queue status, pick-pack processing time, and carrier cutoff times. "
        "Clearly indicate whether the order ships as a single or split shipment, "
        "which warehouse each product ships from, which carrier, cost, and estimated arrival."
    ),
    backstory=(
        "You are a senior fulfillment strategist operating across the Los Angeles warehouse network. "
        "You manage a team of specialized agents and synthesize complex multi-product, "
        "multi-warehouse logistics data — including live world state — into clear, "
        "actionable fulfillment plans. Your decisions are data-driven, real-time, and customer-focused."
    ),
    tools=[],
    verbose=False,
    allow_delegation=True,
)