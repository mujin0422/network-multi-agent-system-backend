from langgraph.types import Command

from src.network_agnets.graph.state import InputAnalysts, InputNetworkExpert, NetworkState, OuputNetworkExpert, ToolRawData

class SupervisorAgent:
    def route(self, state: NetworkState):
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None
        raw_data = {}
        tools_used = []
        tool_results = []

        for msg in reversed(messages):
            if msg.type == "tool":
                tool_name = getattr(msg, "name", "unknown_tool")
                if tool_name not in raw_data:
                    raw_data[tool_name] = msg.content
                    tools_used.append(tool_name)
                    tool_results.append(
                        ToolRawData(
                            tool_name=tool_name,
                            raw_data=str(msg.content),
                        )
                    )
            elif msg.type == "human":
                break

        tools_used.reverse()
        tool_results.reverse()
        
        # 0. KIỂM TRA YÊU CẦU MỚI: Nếu tin nhắn cuối cùng là từ người dùng, bắt đầu thu thập dữ liệu mới
        if last_message and last_message.type == "human":
            print("\033[95m[SUPERVISOR] Nhận yêu cầu mới. Chuyển sang ➤ NETWORK EXPERT ...\033[0m")
            input_network_expert = InputNetworkExpert(
                human_mesage=last_message.content,
            )
            return Command(
                goto="network_expert",
                update={
                    "input_network_expert": input_network_expert,
                }
            )
        
        # 3. CHUYỂN SANG PHÂN TÍCH
        print("\033[95m[SUPERVISOR] Đã có dữ liệu. Thực hiện phân tích với ➤  ANALYST ...\033[0m")
        human_mesage = ""
        for msg in reversed(messages):
            if msg.type == "human":
                human_mesage = msg.content
                break

        output_network_expert = OuputNetworkExpert(
            tools_used=tools_used,
            raw_data=raw_data,
            tool_results=tool_results,
        )
        input_analysts = InputAnalysts(
            tools_used=tools_used,
            raw_data=raw_data,
            human_mesage=human_mesage,
        )

        return Command(
            goto="analyst",
            update={
                "output_network_expert": output_network_expert,
                "input_analysts": input_analysts,
            }
        )
