from graphviz import Digraph


def generate_workflow_graph(workflow_steps=None):
    """
    Generate dynamic workflow graph based on executed steps
    """

    dot = Digraph()

    # Default nodes
    dot.node("User", "User Request")

    previous = "User"

    # If no steps, show static graph
    if not workflow_steps:
        dot.node("Planner", "Planner Agent")
        dot.node("Router", "Router")
        dot.node("Report", "Report")

        dot.edge("User", "Planner")
        dot.edge("Planner", "Router")
        dot.edge("Router", "Report")

        return dot

    # Dynamic graph (REAL ENTERPRISE FEATURE)
    for i, step in enumerate(workflow_steps):

        node_name = f"step_{i}"
        dot.node(node_name, step)

        dot.edge(previous, node_name)

        previous = node_name

    return dot