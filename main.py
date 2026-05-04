import os
import logging
import warnings

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)
os.environ["LITELLM_LOG"] = "ERROR"

import pandas as pd
from world_state import world
from tasks import build_tasks
from crew import build_crew


AGENT_MESSAGES = {
    "Order Intake Specialist":          "Receiving and validating order...",
    "Inventory Manager":                "Checking stock levels across warehouses...",
    "Warehouse Capacity Analyst":       "Evaluating fulfillment strategy (single vs split shipment)...",
    "Carrier and Shipping Evaluator":   "Evaluating carrier options per shipment leg...",
    "Fulfillment Coordinator":          "Synthesizing final fulfillment plan...",
}

from world_state import SHIPPING_TIERS

# Map menu numbers to tier keys using world state definitions
DELIVERY_TIERS = {
    "1": ("standard", SHIPPING_TIERS["standard"]["label"], SHIPPING_TIERS["standard"]["description"], ", ".join(SHIPPING_TIERS["standard"]["services"].values())),
    "2": ("premium",  SHIPPING_TIERS["premium"]["label"],  SHIPPING_TIERS["premium"]["description"],  ", ".join(SHIPPING_TIERS["premium"]["services"].values())),
    "3": ("express",  SHIPPING_TIERS["express"]["label"],  SHIPPING_TIERS["express"]["description"],  ", ".join(SHIPPING_TIERS["express"]["services"].values())),
}

CSV_PATH = "inventory_data.csv"


def print_product_catalog():
    df = pd.read_csv(CSV_PATH)
    df.columns = df.columns.str.strip()

    catalog = (
        df[["Product", "Price"]]
        .drop_duplicates(subset="Product")
        .sort_values("Product")
        .reset_index(drop=True)
    )

    print("\n" + "=" * 50)
    print("  FULFILLMENT COORDINATION SYSTEM")
    print("=" * 50)
    print("  📦 Available Products\n")
    print(f"  {'#':<4} {'Product':<20} {'Price':>8}")
    print(f"  {'─'*4} {'─'*20} {'─'*8}")

    for i, row in catalog.iterrows():
        print(f"  {i+1:<4} {row['Product']:<20} ${row['Price']:>7.2f}")

    print(f"  {'─'*4} {'─'*20} {'─'*8}")
    print(f"  {len(catalog)} products available")


def print_world_disruptions():
    data = world.get_all_disruptions()
    wh_d = data["warehouse_disruptions"]
    ca_d = data["carrier_disruptions"]

    print("\n" + "─" * 50)
    print("  🌍 World State — Active Disruptions")
    print("─" * 50)

    if not wh_d and not ca_d:
        print("  ✅ All warehouses and carriers operating normally.\n")
        return

    if wh_d:
        print("\n  🏭 Warehouse Disruptions:")
        for name, d in wh_d.items():
            print(f"    ⚠️  {name} — {d['label']}")
            print(f"         Reason  : {d['reason']}")
            print(f"         Impact  : {int(d['slowdown_pct']*100)}% pick-pack slowdown")
    else:
        print("\n  🏭 Warehouses: No disruptions")

    if ca_d:
        print("\n  🚚 Carrier Disruptions:")
        for name, d in ca_d.items():
            print(f"    ⚠️  {name} — {d['label']}")
            print(f"         Reason  : {d['reason']}")
            print(f"         Impact  : +{d['delay_days']} day(s) added to all services")
    else:
        print("\n  🚚 Carriers: No disruptions")

    print()


def get_delivery_tier() -> str:
    print("\n" + "─" * 50)
    print("  🚚 Select Delivery Tier")
    print("─" * 50)
    print(f"\n  {'#':<4} {'Tier':<20} {'Speed':<22} Services")
    print(f"  {'─'*4} {'─'*20} {'─'*22} {'─'*35}")

    for key, (_, label, speed, services) in DELIVERY_TIERS.items():
        print(f"  {key:<4} {label:<20} {speed:<22} {services}")

    print()
    while True:
        choice = input("  Enter choice (1/2/3): ").strip()
        if choice in DELIVERY_TIERS:
            tier_key, label, speed, _ = DELIVERY_TIERS[choice]
            print(f"\n  ✅ Selected: {label} ({speed})")
            return tier_key
        print("  ⚠️  Please enter 1, 2, or 3.")


def get_order_from_user() -> dict:
    print("\n" + "─" * 50)
    print("  Enter your order below.")
    print("─" * 50)

    items = []

    while True:
        print()
        product = input("  Product name : ").strip()

        while True:
            try:
                quantity = int(input(f"  Quantity     : ").strip())
                if quantity <= 0:
                    print("  ⚠️  Please enter a quantity greater than 0.")
                    continue
                break
            except ValueError:
                print("  ⚠️  Please enter a valid number.")

        items.append({"product": product, "quantity": quantity})

        more = input("\n  Add more items? (y/n): ").strip().lower()
        if more != "y":
            break

    destination = input("\n  Your location : ").strip()
    tier        = get_delivery_tier()

    return {
        "items":       items,
        "destination": destination,
        "tier":        tier,
    }


def run(order: dict):
    tier_info = DELIVERY_TIERS.get(
        next(k for k, v in DELIVERY_TIERS.items() if v[0] == order["tier"]),
        ("", "Unknown", "", "")
    )

    print("\n" + "─" * 50)
    print("  Order Summary")
    print("─" * 50)
    for item in order["items"]:
        print(f"  • {item['product']} x{item['quantity']}")
    print(f"  Destination  : {order['destination']}")
    print(f"  Delivery     : {tier_info[1]} ({tier_info[2]})")
    print("─" * 50)

    tasks = build_tasks(order)
    crew = build_crew(order, tasks)
    result = crew.kickoff()

    print("\n")
    print(result)
    print()

    return result


if __name__ == "__main__":
    print_product_catalog()
    print_world_disruptions()
    order = get_order_from_user()
    run(order)