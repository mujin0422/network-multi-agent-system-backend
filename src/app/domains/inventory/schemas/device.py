"""Pydantic contracts của Network Inventory domain.

Các model trong file này đồng thời thực hiện ba nhiệm vụ:

- kiểm tra dữ liệu request từ frontend;
- định nghĩa response ổn định của Device API;
- tạo schema và mô tả trường dữ liệu trên Swagger/OpenAPI.

Password và secret không thuộc các model này. Device chỉ tham chiếu tới
``credential_id`` để tránh vô tình trả thông tin nhạy cảm ra frontend.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Device(BaseModel):
    """Device response công khai được trả cho frontend.

    Model chứa metadata và khóa tham chiếu credential, nhưng tuyệt đối không
    chứa username, password hay enable secret.
    """

    id: str = Field(description="Khóa chính, thường dùng prefix devc.")
    credential_id: str | None = Field(
        default=None,
        description="ID credential; null nếu chưa được gán.",
    )
    brand_id: str = Field(description="ID hãng sản xuất.")
    category_id: str = Field(description="ID loại thiết bị.")
    hostname: str = Field(description="Nhãn thiết bị duy nhất.")
    host: str = Field(description="Địa chỉ IP hoặc DNS dùng để kết nối.")
    port: int = Field(gt=0, le=65535, description="Cổng SSH/Telnet.")
    device_type: str = Field(description="Netmiko driver của thiết bị.")
    location: str | None = Field(default=None, description="Vị trí vật lý hoặc logic.")
    created_by: str = Field(description="ID user tạo device; không đổi sau khi tạo.")
    last_updated_by: str | None = Field(
        default=None,
        description="ID user cập nhật device gần nhất.",
    )
    created_at: datetime = Field(description="Thời điểm tạo theo UTC.")
    last_updated_at: datetime = Field(description="Thời điểm cập nhật theo UTC.")


class DevicePage(BaseModel):
    """Một trang kết quả Device cùng metadata phân trang."""

    items: list[Device] = Field(description="Danh sách thiết bị của trang hiện tại.")
    page: int = Field(ge=1, description="Số trang hiện tại, bắt đầu từ 1.")
    page_size: int = Field(ge=1, description="Số thiết bị tối đa trong một trang.")
    total: int = Field(ge=0, description="Tổng số thiết bị khớp bộ lọc.")
    total_pages: int = Field(ge=0, description="Tổng số trang của kết quả.")


class DeviceCreate(BaseModel):
    """Payload frontend gửi khi đăng ký một thiết bị mới."""

    # Loại bỏ khoảng trắng đầu/cuối trước khi service xử lý constraint.
    model_config = ConfigDict(str_strip_whitespace=True)

    credential_id: str | None = Field(
        default=None,
        description="ID credential dùng khi Netmiko kết nối tới thiết bị.",
    )
    brand_id: str = Field(
        min_length=1,
        description="ID hãng sản xuất, ví dụ Cisco hoặc Juniper.",
    )
    category_id: str = Field(
        min_length=1,
        description="ID loại thiết bị, ví dụ Router hoặc Switch.",
    )
    hostname: str = Field(
        min_length=1,
        max_length=255,
        description="Tên duy nhất dùng để nhận diện thiết bị, ví dụ P1.",
    )
    host: str = Field(
        default="127.0.0.1",
        min_length=1,
        description="Địa chỉ IP hoặc DNS mà backend dùng để kết nối.",
    )
    port: int = Field(
        gt=0,
        le=65535,
        description="Cổng SSH/Telnet của thiết bị.",
    )
    device_type: str = Field(
        default="cisco_ios_telnet",
        min_length=1,
        description="Netmiko device_type xác định driver kết nối.",
    )
    location: str | None = Field(
        default=None,
        description="Vị trí vật lý hoặc tên phòng lab của thiết bị.",
    )
    last_updated_by: str = Field(
        min_length=1,
        description="ID người dùng tạo hoặc cập nhật thiết bị.",
    )


class DeviceUpdate(BaseModel):
    """Payload cập nhật một phần; trường không gửi lên sẽ được giữ nguyên.

    ``last_updated_by`` là bắt buộc để luôn xác định được người thực hiện thay
    đổi. Các trường còn lại là tùy chọn theo đúng ý nghĩa của HTTP PATCH.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    credential_id: str | None = Field(default=None, description="Credential mới.")
    brand_id: str | None = Field(default=None, min_length=1, description="Brand mới.")
    category_id: str | None = Field(
        default=None,
        min_length=1,
        description="Category mới.",
    )
    hostname: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Hostname mới.",
    )
    host: str | None = Field(default=None, min_length=1, description="Host/IP mới.")
    port: int | None = Field(default=None, gt=0, le=65535, description="Port mới.")
    device_type: str | None = Field(
        default=None,
        min_length=1,
        description="Netmiko device_type mới.",
    )
    location: str | None = Field(default=None, description="Vị trí mới.")
    last_updated_by: str = Field(min_length=1, description="ID user thực hiện update.")
