import os
import requests
import warnings
import time

from langchain_core.messages import HumanMessage
from src.network_agnets.graph.workflow import createNetworkAssistantGraph
from src.network_agnets.graph.state import NetworkState, DeviceConnection
from src.core.config import settings
from src.core.connection import GNS3_URL_VERS, GNS3_URL_PRJ
from src.utils.console import printRawData
from src.utils.helpers import loadYamlFile, wrapTextLines
from src.utils.logging import getLogger

os.environ["LANGCHAIN_TRACING"] = "false"

logger = getLogger(__name__)

graphInstance = None
deviceObjectInstance = None
warnings.filterwarnings("ignore", message=".*Deserializing unregistered type.*")


def checkGNS3Connectivity() -> bool:
    """Kiểm tra kết nối tới GNS3 Server trước khi khởi động Agent"""
    try:
        response = requests.get(GNS3_URL_VERS, timeout=5)
        response.raise_for_status()
        version = response.json().get("version")
        logger.info(f"Kết nối GNS3 Server thành công (v{version})")
        
        proj_resp = requests.get(GNS3_URL_PRJ, timeout=5)
        if proj_resp.status_code == 200:
            logger.info(f"Project '{proj_resp.json().get('name')}' sẵn sàng.")
            return True
        else:
            logger.error(f"Không tìm thấy Project ID: {settings.PROJECT_ID}")
            return False
    except Exception as e:
        logger.error(f"Lỗi kết nối GNS3: {e}")
        return False


def initializeSystem() -> bool:
    global graphInstance, deviceObjectInstance
    
    print("\n\033[92m[HỆ THỐNG] Bắt đầu khởi tạo ứng dụng...\033[0m")
    
    if not checkGNS3Connectivity():
        return False
    
    device_config = loadDeviceConfig()
    if not device_config:
        logger.error("Không thể load config thiết bị từ devices.yaml")
        return False
    
    deviceObjectInstance = createDeviceConnection(device_config)
    
    try:
        graphInstance = createNetworkAssistantGraph()
        logger.info("Đã khởi tạo LangGraph workflow")
    except Exception as e:
        logger.error(f"Lỗi khởi tạo graph: {e}")
        return False
    
    print("\033[92m[HỆ THỐNG] Khởi tạo hoàn tất!\033[0m\n")
    return True


def loadDeviceConfig():
    try:
        devices = loadYamlFile("config/devices.yaml", default=None)
            
        if devices:
            first_device_key = list(devices.keys())[0]
            return devices.get(first_device_key)
        return None
        
    except Exception as e:
        logger.error(f"Lỗi config: {e}")
        return None

def createDeviceConnection(device_config: dict):
    try:
        return DeviceConnection(
            hostname=str(device_config.get("hostname", "")),
            device_type=str(device_config.get("device_type", "cisco_ios")),
            username=str(device_config.get("username", "")),
            password=str(device_config.get("password", "")),
            secret=str(device_config.get("secret")),
            port=int(device_config.get("port", 22))
        )
    except Exception as e:
        logger.error(f"Lỗi tạo DeviceConnection: {e}"); return None

# --- PROCESS & FORMATTING ---

def processQuery(query: str, thread_id: str = "default", is_resume: bool = False):
    global graphInstance, deviceObjectInstance
    if not graphInstance: return
    
    config = {"configurable": {"thread_id": thread_id}}
    print("\n\033[92m[HỆ THỐNG] Đang xử lý yêu cầu...\033[0m")
    
    try:
        # 1. GỌI ĐỒ THỊ (Khởi tạo mới hoặc Tiếp tục từ điểm bị ngắt)
        if is_resume:
            from langgraph.types import Command
            stream_generator = graphInstance.stream(Command(resume=query), config)
        else:
            initial_state = NetworkState(
                messages=[HumanMessage(content=query)],
            )
            stream_generator = graphInstance.stream(initial_state, config)

        # 2. VÒNG LẶP XỬ LÝ VÀ IN DỮ LIỆU
        for chunk in stream_generator:
            if "network_expert" in chunk:
                messages = chunk["network_expert"].get("messages", [])
                tool_messages = [msg for msg in messages if getattr(msg, "type", "") == "tool"]
                if tool_messages:
                    printRawData(tool_messages, tool_label="Tool đã dùng")

            if "analyst" in chunk:
                # --- IN KHUNG PHÂN TÍCH CỦA ANALYST ---
                msg = chunk["analyst"].get("messages", [])[-1]
                if hasattr(msg, 'content') and msg.content:
                    content_width = 120 
                    wrapped_lines = wrapTextLines(msg.content, width=content_width)
                    
                    frame_width = content_width + 4
                    print("\033[93m\t" + "╔" + "═"*(frame_width-2) + "╗" + "\033[0m")
                    title = "║ [ANALYST] PHẢN HỒI"
                    print("\033[93m\t" + title + " "*(frame_width - len(title) - 1) + "║" + "\033[0m")
                    
                    for line in wrapped_lines:
                        content_line = "║ " + line.ljust(content_width) + " ║"
                        print("\t" + content_line)
                        
                    print("\033[93m\t" + "╚" + "═"*(frame_width-2) + "╝" + "\033[0m")

        # 3. CHỐT CHẶN HITL: Kiểm tra trạng thái Graph sau khi vòng lặp dừng
        state = graphInstance.get_state(config)
        if state.tasks and state.tasks[0].interrupts:
            interrupt_msg = state.tasks[0].interrupts[0].value
            
            print(f"\n\033[91m [CẢNH BÁO BẢO MẬT] AI YÊU CẦU QUYỀN THỰC THI:\033[0m")
            print(f"\033[93m\t{interrupt_msg}\033[0m")
            
            # Hỏi ý kiến user
            user_approval = input("\t\033[92m 👉 Bạn có đồng ý thực thi không? (yes/no): \033[0m").strip()
            
            # Gọi đệ quy hàm processQuery để mở khóa Graph tiếp tục chạy
            processQuery(user_approval, thread_id=thread_id, is_resume=True)
            
    except Exception as e:
        print(f"\n\033[91m[LỖI THỰC THI] {e}\033[0m")

def interactiveMode():
    if not initializeSystem():
        print("\033[91m[LỖI] Khởi tạo thất bại. Vui lòng kiểm tra GNS3 VM và Config.\033[0m")
        return
    
    print("\033[92m╔════════════════════════════════════════════════════════════════════════╗\033[0m")
    print("\033[92m║                          NETWORK AI ASSISTANT                          ║\033[0m")
    print("\033[92m╠────────────────────────────────────────────────────────────────────────╣\033[0m")
    print("\033[92m║ - GNS3 Server: Connected (172.0.0.1)                                   ║\033[0m")
    print("\033[92m║ - Enter your request (Enter Q to quit)                                 ║\033[0m")
    print("\033[92m╚════════════════════════════════════════════════════════════════════════╝\033[0m")
    
    session_thread_id = f"session_cli_{int(time.time())}"
    query_count = 0
    
    while True:
        try:
            print(f"\n[Phiên làm việc #{query_count + 1}]")
            query = input("\t\033[93m ➤  Yêu cầu của bạn: \033[0m").strip()
            
            if query.lower() in ['q', 'exit']: 
                print("\033[92m[HỆ THỐNG] Đang thoát... Tạm biệt!\033[0m")
                break
            if not query: continue
            
            query_count += 1
            processQuery(query, thread_id=session_thread_id)
            
        except KeyboardInterrupt: 
            print("\n\033[91m[HỆ THỐNG] Đã ngắt bởi người dùng.\033[0m")
            break

if __name__ == "__main__":   
    interactiveMode()
