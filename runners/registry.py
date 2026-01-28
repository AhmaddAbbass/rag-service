from runners.graph_rag_runner import GraphRagRunner


def get_runner(runner_type: str):
    if runner_type != "graph":
        raise ValueError(f"Unknown runner_type: {runner_type}")
    return GraphRagRunner()
