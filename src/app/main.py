"""Điểm khởi động HTTP của kiến trúc mới.

Bản legacy khởi tạo GNS3, LangGraph và giao diện người dùng ngay tại entry point.
Bản mới chỉ lắp API router vào FastAPI; nghiệp vụ được tách xuống các tầng bên dưới.
"""

from fastapi import FastAPI

from app.api.route import api_router


app = FastAPI(
    title="Multi-Agent AI Network Automation Platform",
    version="1.0.0"
)


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
