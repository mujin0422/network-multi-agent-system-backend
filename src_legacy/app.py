import time
from typing import Any

import streamlit as st
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from src.network_agnets.graph.state import NetworkState
from src.network_agnets.graph.workflow import createNetworkAssistantGraph
from src.main import checkGNS3Connectivity, createDeviceConnection, loadDeviceConfig
from src.utils.console import printRawData


APP_TITLE = "Network AI Assistant"
APP_CAPTION = "GNS3 network assistant"


def initSessionState() -> None:
    defaults = {
        "graph": None,
        "device_obj": None,
        "thread_id": f"session_streamlit_{int(time.time())}",
        "messages": [],
        "backend_ready": False,
        "backend_error": "",
        "is_waiting_approval": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def initBackend() -> None:
    if st.session_state.backend_ready or st.session_state.backend_error:
        return

    with st.spinner("Đang khởi tạo kết nối GNS3 và nạp Agent..."):
        if not checkGNS3Connectivity():
            st.session_state.backend_error = "Không thể kết nối tới GNS3 Server."
            return

        device_config = loadDeviceConfig()
        if not device_config:
            st.session_state.backend_error = "Không thể tải cấu hình thiết bị từ devices.yaml."
            return

        device_obj = createDeviceConnection(device_config)
        if not device_obj:
            st.session_state.backend_error = "Không thể tạo cấu hình kết nối thiết bị."
            return

        st.session_state.device_obj = device_obj
        st.session_state.graph = createNetworkAssistantGraph()
        st.session_state.backend_ready = True

        if not st.session_state.messages:
            addMessage("assistant", "Khởi tạo thành công. Sẵn sàng hỗ trợ bạn.")


def addMessage(role: str, content: str) -> None:
    st.session_state.messages.append({"role": role, "content": content})


def renderMessages() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def processAi(user_text: str, is_resume: bool = False) -> str | None:
    graph = st.session_state.graph
    device_obj = st.session_state.device_obj
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    final_response = ""

    if not graph:
        return "Agent chưa sẵn sàng. Vui lòng kiểm tra kết nối GNS3."

    try:
        if is_resume:
            stream_generator = graph.stream(
                Command(resume=user_text),
                config,
                stream_mode="updates",
            )
        else:
            initial_state = NetworkState(
                messages=[HumanMessage(content=user_text)],
            )
            stream_generator = graph.stream(
                initial_state,
                config,
                stream_mode="updates",
            )

        for chunk in stream_generator:
            if "network_expert" in chunk:
                messages = chunk["network_expert"].get("messages", [])
                tool_messages = [msg for msg in messages if getattr(msg, "type", "") == "tool"]
                if tool_messages:
                    printRawData(tool_messages)

            if "analyst" in chunk:
                messages = chunk["analyst"].get("messages", [])
                if messages:
                    msg = messages[-1]
                    if hasattr(msg, "content") and msg.content:
                        final_response = msg.content

        state = graph.get_state(config)
        if state.tasks and state.tasks[0].interrupts:
            interrupt_msg = state.tasks[0].interrupts[0].value
            st.session_state.is_waiting_approval = True
            return buildApprovalMessage(interrupt_msg)

        st.session_state.is_waiting_approval = False
        return final_response or "Đã xử lý xong nhưng chưa nhận được phản hồi từ Analyst."

    except Exception as error:
        st.session_state.is_waiting_approval = False
        return f"Lỗi hệ thống: {error}"


def buildApprovalMessage(interrupt_msg: Any) -> str:
    return (
        "**YÊU CẦU PHÊ DUYỆT TỪ HỆ THỐNG:**\n\n"
        f"{interrupt_msg}\n\n"
        "Vui lòng nhập `yes` để đồng ý thực thi, hoặc `no` để hủy bỏ."
    )


def renderSidebar() -> None:
    with st.sidebar:
        st.subheader("Trạng thái")

        if st.session_state.backend_ready:
            st.success("Agent đã sẵn sàng")
        elif st.session_state.backend_error:
            st.error(st.session_state.backend_error)
        else:
            st.info("Đang chờ khởi tạo")

        st.caption(f"Thread: `{st.session_state.thread_id}`")

        if st.button("Tạo phiên mới", use_container_width=True):
            st.session_state.messages = []
            st.session_state.thread_id = f"session_streamlit_{int(time.time())}"
            st.session_state.is_waiting_approval = False
            st.rerun()


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="centered")
    initSessionState()

    st.title(APP_TITLE)
    st.caption(APP_CAPTION)

    renderSidebar()
    initBackend()
    renderMessages()

    if st.session_state.backend_error:
        st.stop()

    placeholder = (
        "Nhập yes/no để phê duyệt..."
        if st.session_state.is_waiting_approval
        else "Nhập yêu cầu kiểm tra hệ thống mạng..."
    )

    user_text = st.chat_input(placeholder, disabled=not st.session_state.backend_ready)
    if not user_text:
        return

    addMessage("user", user_text)
    with st.chat_message("user"):
        st.markdown(user_text)

    is_resume = st.session_state.is_waiting_approval

    with st.chat_message("assistant"):
        with st.spinner("Đang quét sơ đồ và phân tích..."):
            response = processAi(user_text, is_resume=is_resume)
        st.markdown(response)

    addMessage("assistant", response)
    st.rerun()


if __name__ == "__main__":
    main()
