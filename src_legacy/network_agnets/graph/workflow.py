from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from src.network_agnets.graph.state import NetworkState
from src.network_agnets.agents.supervisor import SupervisorAgent
from src.network_agnets.agents.network_expert import create_network_expert
from src.network_agnets.agents.analyst import create_analyst

def createNetworkAssistantGraph():
    # Khởi tạo các thành phần
    supervisor = SupervisorAgent()
    network_expert = create_network_expert()
    analyst = create_analyst()

    # Khởi tạo đồ thị với NetworkState
    builder = StateGraph(NetworkState)

    #  Định nghĩa các Node
    builder.add_node("supervisor", supervisor.route)
    builder.add_node("network_expert", network_expert)
    builder.add_node("analyst", analyst)

    # Thiết lập luồng chạy (Edges)
    builder.add_edge(START, "supervisor")
    builder.add_edge("network_expert", "supervisor")
    builder.add_edge("analyst", END)

    # Biên dịch đồ thị với bộ nhớ checkpoint
    graph = builder.compile(checkpointer=MemorySaver())

    return graph
