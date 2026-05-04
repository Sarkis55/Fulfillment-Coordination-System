from crewai import Crew, Process
from agents import (
    order_intake_agent,
    inventory_agent,
    capacity_agent,
    shipping_agent,
    coordinator_agent,
)


AGENT_STEPS = [
    ("Order Intake Specialist",         "Receiving and validating order details..."),
    ("Inventory Manager",               "Checking stock levels across all locations..."),
    ("Warehouse Capacity Analyst",      "Evaluating warehouse capacity and readiness..."),
    ("Carrier and Shipping Evaluator",  "Evaluating carrier and shipping options..."),
    ("Fulfillment Coordinator",         "Synthesizing the optimal fulfillment plan..."),
]


def print_agent_start(index):
    agent, task = AGENT_STEPS[index]
    print(f"\n  🚀 {agent}")
    print(f"     ↳ {task}")
    print(f"{'─'*50}")


def make_task_callback():
    counter = {"index": 0}

    def task_callback(task_output):
        agent, _ = AGENT_STEPS[counter["index"]]
        print(f"  ✅ {agent} — Done")
        print(f"{'─'*50}")

        counter["index"] += 1

        if counter["index"] < len(AGENT_STEPS):
            print_agent_start(counter["index"])

    return task_callback


def build_crew(order: dict, tasks: list) -> Crew:
    """
    Assembles the fulfillment crew.
    Tasks are built externally and passed in to avoid circular imports.
    """
    print_agent_start(0)

    crew = Crew(
        agents=[
            order_intake_agent,
            inventory_agent,
            capacity_agent,
            shipping_agent,
        ],
        tasks=tasks,
        process=Process.hierarchical,
        manager_agent=coordinator_agent,
        task_callback=make_task_callback(),
        verbose=False,
    )

    return crew