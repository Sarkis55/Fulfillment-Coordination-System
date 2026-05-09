# Fulfillment Coordination System
by Sarkis Shil-Gevorkyan


-----
## Project Overview

Order fulfillment is more complex than simply receiving an order and shipping a package. A real fulfillment system has to decide which warehouse should handle the order, whether multiple items should be shipped together or split across locations, whether a warehouse has enough pick-pack capacity, and which carrier can meet the promised delivery window.

This project models that problem as a multi-agent coordination system. Instead of using one large decision-making block, the system separates the fulfillment process into specialized agents. Each agent focuses on one part of the problem, then the coordinator combines their results into a final fulfillment recommendation.

## Technical Objective

The technical objective of this project is to demonstrate how a multi-agent system can improve fulfillment planning in a changing environment. The system is designed to:

- Accept customer orders with one or more products
- Check inventory across multiple warehouse locations
- Evaluate whether a single warehouse can fulfill the full order
- Create a split-shipment plan when needed
- Check warehouse queue status and pick-pack capacity
- Account for random warehouse and carrier disruptions
- Check carrier cutoff times and delivery tiers
- Produce a final coordinated fulfillment plan

## Architecture

The system follows a **fan-out / fan-in architecture**.

In the **fan-out stage**, the incoming order is broken into smaller tasks and sent to specialized agents:

- **Order Intake Specialist** validates and structures the order
- **Inventory Manager** checks product availability across warehouses
- **Warehouse Capacity Analyst** evaluates warehouse readiness, queues, and pick-pack rates
- **Carrier and Shipping Evaluator** checks shipping options, delivery tiers, carrier cutoffs, and delays

In the **fan-in stage**, the **Fulfillment Coordinator** gathers the results from the other agents and produces one final recommendation. This recommendation considers inventory, capacity, disruptions, shipment type, carrier availability, cost, and delivery speed.

This structure makes the system easier to understand, expand, and debug because each agent has a specific responsibility.

## Current Features

- Terminal-based order entry
- Product catalog loaded from `inventory_data.csv`
- Multi-product order support
- Delivery tier selection: standard, premium, and express
- Inventory checks across Los Angeles-area warehouses
- Single-shipment vs. split-shipment fulfillment planning
- Warehouse queue and pick-pack capacity modeling
- Random warehouse disruptions
- Random carrier disruptions
- Carrier cutoff checks
- Simulated world state using SimPy
- CrewAI-based agent workflow

## Agents

| Agent | Responsibility |
|---|---|
| Order Intake Specialist | Receives and validates customer order details |
| Inventory Manager | Checks stock availability across warehouse locations |
| Warehouse Capacity Analyst | Evaluates warehouse capacity, queue status, and processing time |
| Carrier and Shipping Evaluator | Evaluates carrier options, delivery tiers, cutoff times, and delays |
| Fulfillment Coordinator | Combines agent outputs and creates the final fulfillment plan |

## Project Files

| File | Purpose |
|---|---|
| `main.py` | Runs the terminal application, displays catalog, collects user input, and starts the crew |
| `agents.py` | Defines the CrewAI agents and their responsibilities |
| `tasks.py` | Builds the task sequence for the agents |
| `crew.py` | Creates the CrewAI crew using a hierarchical process |
| `tools.py` | Contains inventory, warehouse, and fulfillment planning tools |
| `world_state.py` | Defines the simulated environment, warehouses, carriers, tiers, and disruptions |
| `world_state_tools.py` | Provides CrewAI tools for accessing world state information |
| `inventory_data.csv` | Stores warehouse inventory data |
| `requirements.txt` | Lists the required Python dependencies |

## Requirements

This project uses:

- Python 3.10+
- CrewAI
- pandas
- OpenAI
- SimPy
- python-dotenv

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Setup

Clone the repository:

```bash
git clone git@github.com:Sarkis55/Fulfillment-Coordination-System.git
cd Fulfillment-Coordination-System
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows, use:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file if your CrewAI/OpenAI setup requires an API key:

```bash
OPENAI_API_KEY=your_api_key_here
```

## How to Run

Run the system from the project folder:

```bash
python main.py
```

The program will:

1. Display the available product catalog
2. Show active warehouse and carrier disruptions
3. Ask the user to enter products and quantities
4. Ask for the user's location
5. Ask for a delivery tier
6. Run the CrewAI agents
7. Print the final fulfillment recommendation

## Example Workflow

A user may enter an order such as:

```text
Product name : Keyboard
Quantity     : 2
Add more items? y
Product name : Monitor
Quantity     : 1
Your location : Burbank
Delivery tier : Premium Delivery
```

## Status

This project is currently a working prototype. It is designed for demonstration and learning purposes, but the architecture can be expanded into a more realistic fulfillment coordination platform with real APIs, a user interface, and stronger multi-order prioritization.
