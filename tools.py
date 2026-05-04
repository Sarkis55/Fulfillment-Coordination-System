import pandas as pd
from crewai.tools import tool

CSV_PATH = "inventory_data.csv"


def load_inventory() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH)
    df.columns = df.columns.str.strip()
    return df


@tool("Check Inventory Availability")
def check_inventory(product: str) -> str:
    """
    Check stock availability for a given product across all locations.
    Input: product name (string).
    Returns: inventory levels per location, highlighting out-of-stock sites.
    """
    df = load_inventory()
    results = df[df["Product"].str.lower() == product.lower()]

    if results.empty:
        return f"No inventory records found for product: '{product}'."

    in_stock = results[results["Inventory Level"] > 0]
    out_of_stock = results[results["Inventory Level"] == 0]

    output = f"Inventory for '{product}':\n"
    output += "\n  IN STOCK locations:\n"
    if in_stock.empty:
        output += "    None — product is out of stock everywhere.\n"
    else:
        for _, row in in_stock.iterrows():
            output += (
                f"    - {row['Location']}: {row['Inventory Level']} units available "
                f"| Units Sold: {row['Units Sold']} | Price: ${row['Price']}\n"
            )

    if not out_of_stock.empty:
        output += "\n  OUT OF STOCK locations:\n"
        for _, row in out_of_stock.iterrows():
            output += f"    - {row['Location']} (0 units)\n"

    return output


@tool("Get Warehouse Capacity")
def get_warehouse_capacity(location: str) -> str:
    """
    Get total available stock and capacity details for a given warehouse/location.
    Input: location name (string).
    Returns: summary of all products and stock levels at that location.
    """
    df = load_inventory()
    results = df[df["Location"].str.lower() == location.lower()]

    if results.empty:
        return f"No warehouse data found for location: '{location}'."

    total_stock = results["Inventory Level"].sum()
    in_stock_count = (results["Inventory Level"] > 0).sum()
    out_of_stock_count = (results["Inventory Level"] == 0).sum()

    output = f"Warehouse '{location}' summary:\n"
    output += f"  Total Stock Units    : {total_stock}\n"
    output += f"  Products In Stock    : {in_stock_count}\n"
    output += f"  Products Out of Stock: {out_of_stock_count}\n"
    output += "\n  Full product list:\n"

    for _, row in results.sort_values("Inventory Level", ascending=False).iterrows():
        status = "✓" if row["Inventory Level"] > 0 else "✗ OUT OF STOCK"
        output += (
            f"    {status} {row['Product']}: {row['Inventory Level']} units @ ${row['Price']}\n"
        )

    return output


@tool("List All Locations")
def list_all_locations() -> str:
    """
    Returns all warehouse/store locations in the inventory dataset.
    No input needed.
    """
    df = load_inventory()
    locations = df["Location"].dropna().unique().tolist()
    return f"Available warehouse locations: {', '.join(sorted(locations))}"


@tool("Find Best Fulfillment Plan For Order")
def find_best_fulfillment_plan(order_items: str) -> str:
    """
    Given a list of products and quantities, determines the optimal fulfillment plan.
    Tries to find a single location that can fulfill all items.
    If not possible, identifies the best split fulfillment across multiple locations.

    Input: comma-separated list in format 'Product:Quantity' 
           e.g. 'Graphics Card:2,Keyboard:5,Monitor:1'
    Returns: fulfillment plan indicating single or split shipment.
    """
    df = load_inventory()

    # Parse input
    try:
        items = {}
        for pair in order_items.split(","):
            product, qty = pair.strip().split(":")
            items[product.strip()] = int(qty.strip())
    except Exception:
        return "Invalid input format. Use 'Product:Quantity' pairs separated by commas."

    all_locations = df["Location"].unique().tolist()

    # ── Step 1: Try to find a single location that has ALL items ──
    single_location_candidates = []

    for location in all_locations:
        loc_df = df[df["Location"].str.lower() == location.lower()]
        can_fulfill_all = True
        details = []

        for product, qty_needed in items.items():
            match = loc_df[loc_df["Product"].str.lower() == product.lower()]
            if match.empty or match.iloc[0]["Inventory Level"] < qty_needed:
                can_fulfill_all = False
                break
            details.append(f"{product}: {match.iloc[0]['Inventory Level']} available (need {qty_needed})")

        if can_fulfill_all:
            single_location_candidates.append((location, details))

    if single_location_candidates:
        output = "✅ SINGLE SHIPMENT POSSIBLE — All items can ship from one location:\n\n"
        for location, details in single_location_candidates:
            output += f"  📦 {location}:\n"
            for d in details:
                output += f"      - {d}\n"
        return output

    # ── Step 2: No single location — find best split fulfillment ──
    output = "⚠️  SPLIT SHIPMENT REQUIRED — No single location can fulfill all items.\n\n"
    output += "  Best fulfillment per product:\n\n"

    unfullfillable = []

    for product, qty_needed in items.items():
        product_df = df[
            (df["Product"].str.lower() == product.lower()) &
            (df["Inventory Level"] >= qty_needed)
        ].sort_values("Inventory Level", ascending=False)

        partial_df = df[
            (df["Product"].str.lower() == product.lower()) &
            (df["Inventory Level"] > 0) &
            (df["Inventory Level"] < qty_needed)
        ].sort_values("Inventory Level", ascending=False)

        if not product_df.empty:
            best = product_df.iloc[0]
            output += f"  📦 {product} (need {qty_needed}):\n"
            output += f"      → Ship from: {best['Location']} ({best['Inventory Level']} units available @ ${best['Price']})\n\n"
        elif not partial_df.empty:
            output += f"  ⚠️  {product} (need {qty_needed}) — Partial stock only:\n"
            for _, row in partial_df.iterrows():
                output += f"      - {row['Location']}: {row['Inventory Level']} units available\n"
            output += f"      → Consider splitting {product} across multiple locations.\n\n"
        else:
            unfullfillable.append(product)

    if unfullfillable:
        output += f"  ❌ OUT OF STOCK everywhere — cannot fulfill: {', '.join(unfullfillable)}\n"

    return output


@tool("Estimate Shipping Options")
def estimate_shipping_options(location: str) -> str:
    """
    Estimates shipping carriers, costs, and delivery times from a warehouse location.
    Input: warehouse location name (string).
    Returns: available carrier options with cost and estimated delivery days.
    """
    shipping_data = {
        "northridge": [
            {"carrier": "FedEx", "days": 1, "cost": 9.99},
            {"carrier": "UPS",   "days": 2, "cost": 5.99},
            {"carrier": "USPS",  "days": 3, "cost": 1.99},
        ],
        "long beach": [
            {"carrier": "FedEx", "days": 1, "cost": 9.99},
            {"carrier": "UPS",   "days": 2, "cost": 5.49},
            {"carrier": "USPS",  "days": 3, "cost": 1.99},
        ],
        "ontario": [
            {"carrier": "FedEx", "days": 3, "cost": 1.99},
            {"carrier": "UPS",   "days": 2, "cost": 5.99},
            {"carrier": "USPS",  "days": 1, "cost": 9.99},
        ],
        "santa monica": [
            {"carrier": "FedEx", "days": 1, "cost": 9.99},
            {"carrier": "UPS",   "days": 2, "cost": 5.99},
            {"carrier": "USPS",  "days": 3, "cost": 1.99},
        ],
        "monterey park": [
            {"carrier": "FedEx", "days": 2, "cost": 5.99},
            {"carrier": "UPS",   "days": 3, "cost": 1.99},
            {"carrier": "USPS",  "days": 1, "cost": 9.99},
        ],
    }

    key = location.lower()
    options = shipping_data.get(key, [
        {"carrier": "FedEx", "days": 1, "cost": 9.99},
        {"carrier": "UPS",   "days": 2, "cost": 5.99},
        {"carrier": "USPS",  "days": 3, "cost": 1.99},
    ])

    output = f"Shipping options from '{location}':\n"
    for opt in options:
        output += f"  - {opt['carrier']}: {opt['days']} day(s) | ${opt['cost']}\n"
    return output