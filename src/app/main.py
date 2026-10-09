"""Điểm khởi động HTTP của kiến trúc mới.

Bản legacy khởi tạo GNS3, LangGraph và giao diện người dùng ngay tại entry point.
Bản mới chỉ lắp API router vào FastAPI; nghiệp vụ được tách xuống các tầng bên dưới.
"""

from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.route import api_router
from app.core.config import get_settings


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.app_debug,
)

# Domain service ném lỗi nghiệp vụ độc lập với HTTP; lớp API chịu trách nhiệm
# chuyển chúng thành status code ổn định để frontend dễ xử lý.
register_error_handlers(app)


# Tất cả endpoint nghiệp vụ dùng chung tiền tố /api; health check được giữ độc lập
# để hạ tầng giám sát có thể kiểm tra tiến trình mà không chạy qua agent.
app.include_router(
    api_router,
    prefix="/api"
)


@app.get("/health")
async def health_check():
    return {
        "status": "running"
    }
