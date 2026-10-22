# Luồng tạo Conversation từ Message đầu tiên

## Mục tiêu

Backend không tạo `Conversation` khi người dùng chỉ mở trang Chatbot. Một
Conversation mới chỉ được tạo khi người dùng thực sự nhấn gửi yêu cầu đầu tiên.
Cách này tránh sinh Conversation rỗng trong database và giữ frontend đơn giản.

## Phân chia trách nhiệm

### Frontend

- Trang chat mới giữ `conversation_id = null`.
- Khi người dùng gửi lần đầu, gọi `POST /api/v1/conversations/messages`.
- Không gửi `user_id`, `sender_by`, `message_type` hoặc `title`.
- Sau khi nhận response, lưu `conversation.id`, cập nhật URL/sidebar và hiển thị
  title do backend trả về.
- Các Message tiếp theo gọi
  `POST /api/v1/conversations/{conversation_id}/messages`.

### Backend

- Lấy User hiện tại từ Access Token.
- Tạo Conversation và USER_REQUEST đầu tiên trong cùng một transaction.
- Gọi LLM tạo title từ nội dung USER_REQUEST đầu tiên.
- Dùng fallback từ nội dung Message nếu thiếu cấu hình LLM, timeout hoặc lỗi.
- Chuẩn hóa title thành một dòng, không có Markdown và tối đa 100 ký tự.
- Chỉ tự động tạo title trong endpoint khởi tạo Conversation.
- Tiếp tục pipeline GNS3 check, Planning và Execution sau khi dữ liệu nguồn đã
  được lưu thành công.

## API bắt đầu Conversation

```http
POST /api/v1/conversations/messages
Authorization: Bearer <access_token>
Content-Type: application/json
```

Request:

```json
{
  "message": "Kiểm tra routing table trên P1"
}
```

Backend tự xác định:

```text
conversation.user_id = authenticated_user.id
conversation.title = "Cuộc hội thoại mới" (tạm thời)
message.sender_by = USER
message.message_type = USER_REQUEST
message.reply_to_message_id = NULL
```

Response:

```json
{
  "conversation": {
    "id": "cons-211026-a1b2c3d4",
    "user_id": "user-221026-00000001",
    "title": "Kiểm tra routing table trên P1",
    "created_at": "2026-10-21T09:30:00+07:00",
    "last_updated_at": "2026-10-21T09:30:01+07:00"
  },
  "message": {
    "id": "mesg-211026-e5f6a7b8",
    "conversation_id": "cons-211026-a1b2c3d4",
    "reply_to_message_id": null,
    "sender_by": "USER",
    "message_type": "USER_REQUEST",
    "message": "Kiểm tra routing table trên P1",
    "created_at": "2026-10-21T09:30:00+07:00"
  }
}
```

## Trình tự xử lý

```text
Frontend: conversation_id = null
        │
        │ POST /api/v1/conversations/messages
        ▼
ConversationService.start()
        │
        ├── Tạo Conversation với title tạm
        ├── Tạo USER_REQUEST đầu tiên
        └── ConversationRepository.create_with_first_message()
                └── COMMIT một transaction
        │
        ▼
ConversationTitleGenerator.generate()
        │
        ├── Gọi NVIDIA LLM nếu đã cấu hình
        └── Fallback nếu thiếu cấu hình, lỗi hoặc timeout
        │
        ▼
ConversationService.update_title()
        │
        ▼
GNS3 availability check
        │
        ▼
PlanningOrchestrator.plan_user_message()
        │
        ▼
ExecutionOrchestrator.execute_task()
        │
        ▼
Trả Conversation + Message đầu tiên cho Frontend
```

## Transaction và xử lý lỗi

Conversation và Message đầu tiên phải được tạo nguyên tử. Nếu một trong hai
INSERT thất bại, transaction rollback và không để lại Conversation rỗng.

LLM không được gọi bên trong transaction database. Nếu LLM lỗi hoặc vượt quá
`CONVERSATION_TITLE_TIMEOUT_SECONDS`, backend dùng nội dung USER_REQUEST đã
chuẩn hóa làm title. Lỗi tạo title không làm mất Message và không ngăn việc tạo
Task.

Nếu GNS3, Planner hoặc Execution thất bại sau đó, Conversation và USER_REQUEST
vẫn được giữ lại để người dùng thấy lịch sử yêu cầu và hệ thống có thể truy vết
lỗi.

## Message tiếp theo

Sau lần đầu, frontend sử dụng endpoint hiện có:

```http
POST /api/v1/conversations/{conversation_id}/messages
```

Endpoint `POST /api/v1/conversations/` không còn được công khai để tránh tạo
Conversation chưa có Message.

## Các file triển khai chính

- `src/app/domains/conversation/routers/conversation.py`
- `src/app/domains/conversation/services/conversation.py`
- `src/app/domains/conversation/services/title.py`
- `src/app/domains/conversation/repositories/conversation.py`
- `src/app/domains/conversation/utils/title.py`
