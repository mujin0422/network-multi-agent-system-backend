# BÁO CÁO CUỐI KỲ

## HỆ THỐNG MULTI-AGENT HỖ TRỢ QUẢN TRỊ, CẤU HÌNH VÀ CHẨN ĐOÁN SỰ CỐ MẠNG

### Tóm tắt

Đề tài xây dựng một nền tảng hỗ trợ quản trị mạng từ yêu cầu ngôn ngữ tự nhiên, trong đó yêu cầu của người vận hành được chuyển thành kế hoạch thực thi có cấu trúc, ánh xạ tới các thiết bị hợp lệ trong kho tài nguyên, thực thi lệnh đọc hoặc lệnh cấu hình và tổng hợp kết quả bằng các tác tử có trách nhiệm tách biệt. Hệ thống hiện gồm Planner Agent, Network Agent và Analyst Agent; lớp điều phối quản lý kế hoạch dạng đồ thị phụ thuộc, trạng thái thực thi, phê duyệt thao tác ghi và nhật ký kiểm toán. Backend được xây dựng bằng FastAPI và PostgreSQL; kết nối thiết bị sử dụng Netmiko hoặc Nornir; mô hình ngôn ngữ được truy cập thông qua NVIDIA API; môi trường mạng thử nghiệm được mô phỏng bằng GNS3. Giao diện quản trị được xây dựng bằng React và TypeScript.

Báo cáo này phân biệt rõ ba mức độ: thành phần đã được triển khai trong mã nguồn, thành phần mới tồn tại ở mức mô hình dữ liệu hoặc thiết kế, và thành phần chưa được triển khai. LangGraph hiện quản lý luồng cấp cao từ kiểm tra môi trường, lập kế hoạch, thực thi đến phân tích; business state vẫn được lưu trong PostgreSQL. GNS3 API mới được dùng để kiểm tra khả dụng của máy chủ; chưa có dữ liệu thực nghiệm định lượng cho các tác vụ cấu hình, chẩn đoán và khắc phục sự cố. Vì vậy, các mục tương ứng với kết quả chưa tồn tại được giữ trống nhằm bảo đảm tính trung thực khoa học.

**Từ khóa:** Large Language Model, AI Agent, Multi-Agent System, Intent-Based Networking, Network Automation, Network Troubleshooting, Human-in-the-loop, Netmiko, Nornir, GNS3.

---

# CHƯƠNG 1. GIỚI THIỆU VẤN ĐỀ VÀ TỔNG QUAN TÌNH HÌNH NGHIÊN CỨU

## 1.1. Bài toán quản trị và tự động hóa mạng

Hạ tầng mạng hiện đại thường bao gồm nhiều loại thiết bị, phiên bản hệ điều hành, giao thức và miền quản trị. Một thay đổi tưởng như cục bộ, chẳng hạn cập nhật địa chỉ IP, chính sách định tuyến hoặc VLAN, có thể ảnh hưởng đến nhiều thành phần phụ thuộc. Quản trị thủ công bằng giao diện dòng lệnh đòi hỏi người vận hành phải nhớ cú pháp theo nhà cung cấp, xác định đúng thứ tự thao tác, kiểm tra trạng thái trước và sau thay đổi, đồng thời lưu lại bằng chứng phục vụ truy vết. Khi quy mô tăng, phương pháp này phát sinh ba nhóm vấn đề chính: chi phí vận hành cao, kết quả thiếu đồng nhất và rủi ro sai sót do con người.

Tự động hóa mạng chuyển các thao tác lặp lại thành quy trình có thể lập trình. Tuy nhiên, tự động hóa không chỉ là gửi một tập lệnh tới nhiều thiết bị. Một hệ thống phù hợp cần quản lý inventory, thông tin xác thực, quan hệ phụ thuộc giữa các bước, trạng thái từng thiết bị, cơ chế xử lý lỗi, kiểm tra kết quả và nhật ký kiểm toán. Đối với thao tác làm thay đổi cấu hình, hệ thống còn phải bảo đảm đúng đối tượng, đúng nội dung đã được phê duyệt và không thực thi khi điều kiện an toàn chưa thỏa mãn.

RFC 8969 mô tả tự động hóa quản lý dịch vụ và mạng như một vòng đời gồm tạo lập, cung cấp, giám sát, chẩn đoán, bảo đảm và tối ưu dịch vụ; các mô hình dữ liệu đóng vai trò liên kết trạng thái mong muốn với trạng thái vận hành [2]. Cách nhìn theo vòng đời cho thấy một giải pháp tự động hóa hoàn chỉnh phải vượt ra ngoài việc sinh lệnh: nó cần có khả năng kiểm tra, quan sát và phản hồi.

## 1.2. Ứng dụng AI và LLM trong quản trị mạng

Mô hình ngôn ngữ lớn (Large Language Model — LLM) cung cấp một lớp giao tiếp ngữ nghĩa giữa ý định của người vận hành và các thao tác kỹ thuật. Thay vì yêu cầu người dùng chỉ định toàn bộ câu lệnh, LLM có thể phân loại nhiệm vụ, tách yêu cầu thành các bước, lựa chọn dữ liệu cần thu thập và diễn giải kết quả. Trong quản trị mạng, khả năng này đặc biệt hữu ích vì yêu cầu thường được mô tả ở mức mục tiêu, trong khi thực thi cần biểu diễn cụ thể theo thiết bị và giao thức.

Tuy nhiên, đầu ra của LLM có tính xác suất và có thể chứa thiết bị không tồn tại, cú pháp không hợp lệ hoặc suy luận thiếu bằng chứng. Vì vậy, LLM không nên được xem là nguồn chân lý duy nhất và không nên trực tiếp nắm giữ thông tin xác thực hay quyền thay đổi cấu hình. Kiến trúc an toàn cần đặt LLM sau các ranh giới kiểm soát: cung cấp inventory giới hạn, buộc đầu ra theo schema, kiểm tra lại định danh, phân biệt quyền đọc/ghi, phê duyệt thao tác rủi ro và lưu toàn bộ dấu vết thực thi.

Mô hình ReAct cho thấy việc xen kẽ suy luận và hành động giúp mô hình cập nhật kế hoạch dựa trên quan sát từ môi trường [4]. Dù đề tài không cài đặt ReAct theo đúng thuật toán của công trình này, nguyên tắc tách bước lập kế hoạch, hành động và quan sát là cơ sở hữu ích để thiết kế quy trình tác tử có thể kiểm soát.

## 1.3. Các nghiên cứu về cấu hình mạng tự động

Các nghiên cứu gần đây tập trung vào việc chuyển chính sách hoặc yêu cầu ngôn ngữ tự nhiên thành cấu hình mức thấp. NETBUDDY sử dụng LLM để biến yêu cầu cấp cao thành cấu hình P4 và BGP, đồng thời chia quá trình sinh cấu hình thành các bước nhỏ và sử dụng cơ chế tự sửa nhằm cải thiện kết quả [6]. LLM-NetCFG đề xuất các tác tử cấu hình trong định hướng Zero-touch Network and Service Management, kết hợp sinh, xác minh và triển khai cấu hình từ intent ngôn ngữ tự nhiên [7]. Một hướng khác sử dụng các LLM Agent để dịch cấu hình giữa các nền tảng nhà cung cấp, kết hợp phân rã cấu hình theo intent và xác minh hai giai đoạn về cú pháp và ngữ nghĩa [8].

Các công trình này cho thấy ba xu hướng. Thứ nhất, yêu cầu cấp cao cần được phân rã thành đơn vị nhỏ để giảm độ phức tạp của từng lần sinh. Thứ hai, kết quả sinh bởi LLM cần qua lớp xác minh độc lập. Thứ ba, đánh giá phải xem xét cả tính đúng cú pháp và tính đúng ngữ nghĩa; một cấu hình được thiết bị chấp nhận chưa chắc đã đạt mục tiêu vận hành.

Đề tài kế thừa tư tưởng phân rã bằng cách biểu diễn yêu cầu thành các operation có thứ tự và dependency. Tuy nhiên, phiên bản hiện tại chưa có bộ kiểm tra cú pháp theo nền tảng, mô phỏng cấu hình trước khi áp dụng hoặc xác minh hình thức đối với trạng thái đích. Do đó, phạm vi hiện tại là nguyên mẫu có kiểm soát, chưa phải hệ thống cấu hình tự trị hoàn toàn.

## 1.4. Các nghiên cứu về network troubleshooting

Network troubleshooting là quá trình phát hiện triệu chứng, thu thập dữ liệu liên quan, khoanh vùng miền lỗi, suy luận nguyên nhân gốc và đề xuất hoặc thực hiện biện pháp khắc phục. Phương pháp truyền thống dựa trên runbook, luật chuyên gia, so sánh cấu hình và tương quan sự kiện. Trong hệ thống lớn, dữ liệu có thể đến từ log, trạng thái giao thức, bảng định tuyến, chỉ số hiệu năng và topology; vì vậy, thách thức cốt lõi là liên kết bằng chứng phân tán với quan hệ phụ thuộc giữa các dịch vụ và thiết bị.

RFC 9232 mô tả mức trưởng thành của telemetry từ thu thập dữ liệu tới vòng điều khiển khép kín, trong đó hệ thống thông minh tự động yêu cầu dữ liệu, phân tích và cập nhật hoạt động mạng [9]. Các nghiên cứu LLM cho Root Cause Analysis gần đây nhấn mạnh rằng LLM thuần túy dễ tạo suy luận không ổn định; kết quả cần được ràng buộc bởi bằng chứng có cấu trúc và tri thức miền [10].

Trong đề tài, Planner Agent có thể tạo các bước thu thập bằng lệnh `show`, Network Agent lấy kết quả thực tế, và Analyst Agent tổng hợp phát hiện, nguyên nhân có khả năng cùng khuyến nghị. Cơ chế này hỗ trợ phân tích dựa trên output đã thu thập, nhưng chưa có telemetry liên tục, knowledge graph, bộ luật RCA hoặc tập benchmark sự cố đã gán nhãn. Vì vậy, kết quả hiện tại nên được gọi là phân tích hỗ trợ chẩn đoán, không phải khẳng định nguyên nhân gốc với độ tin cậy đã được kiểm chứng.

## 1.5. Multi-Agent trong quản trị và xử lý sự cố hệ thống

Multi-Agent System (MAS) phân chia một nhiệm vụ phức tạp cho nhiều tác tử có vai trò và giao diện rõ ràng. Trong ứng dụng LLM, AutoGen minh họa khả năng tổ chức các tác tử hội thoại để phối hợp hoàn thành nhiệm vụ [5]. Lợi ích của cách tiếp cận nhiều tác tử không nằm ở số lượng tác tử, mà ở khả năng cô lập trách nhiệm và quyền hạn: tác tử lập kế hoạch không cần quyền truy cập credential; tác tử thực thi không cần tự suy luận mục tiêu; tác tử phân tích không được tự thay đổi thiết bị.

Đối với quản trị mạng, phân tách này giúp giảm phạm vi ảnh hưởng khi một thành phần trả kết quả sai. Planner tạo kế hoạch nhưng không kết nối thiết bị. Network Agent chỉ nhận operation và mapping đã được kiểm tra. Analyst chỉ xử lý output sau thực thi. Orchestrator, thay vì LLM, quản lý trạng thái, dependency, phê duyệt và ghi audit. Đây là mô hình “AI đề xuất — phần mềm xác minh và thực thi” phù hợp hơn với yêu cầu kiểm soát thay đổi.

## 1.6. Nhận xét các nghiên cứu liên quan

| Hướng nghiên cứu | Đóng góp chính | Hạn chế cần lưu ý khi áp dụng |
| --- | --- | --- |
| Intent-Based Networking | Trừu tượng hóa mục tiêu khỏi chi tiết thiết bị; nhấn mạnh fulfillment và assurance | Cần mô hình intent, cơ chế dịch và vòng phản hồi đáng tin cậy |
| LLM sinh cấu hình | Giảm rào cản cú pháp; hỗ trợ biến yêu cầu tự nhiên thành cấu hình | Có nguy cơ hallucination, sai cú pháp hoặc đúng cú pháp nhưng sai mục tiêu |
| LLM hỗ trợ troubleshooting | Tổng hợp nhiều bằng chứng và tạo giải thích dễ hiểu | Cần grounding, telemetry và benchmark RCA; không nên suy luận khi thiếu dữ liệu |
| Multi-Agent | Phân tách trách nhiệm, chuyên môn và quyền hạn | Tăng độ phức tạp điều phối, trạng thái và xử lý lỗi liên tác tử |
| Closed-loop automation | Theo dõi trạng thái thực tế và hiệu chỉnh để duy trì intent | Đòi hỏi quan sát liên tục, kiểm tra hậu điều kiện, rollback và quản trị rủi ro |

Nhìn chung, các nghiên cứu khẳng định tiềm năng của LLM trong giao diện intent và lập kế hoạch, nhưng cũng thống nhất gián tiếp về nhu cầu xác minh ngoài mô hình. Khoảng cách lớn giữa nguyên mẫu và triển khai thực tế nằm ở dữ liệu đánh giá, kiểm soát tác động, khả năng phục hồi và chứng minh rằng trạng thái sau thực thi phù hợp với mục tiêu ban đầu.

## 1.7. Khoảng trống nghiên cứu và hướng tiếp cận của đề tài

Khoảng trống mà đề tài hướng tới là xây dựng một luồng end-to-end có thể truy vết cho yêu cầu quản trị mạng bằng tiếng Việt, đồng thời hạn chế quyền tự quyết trực tiếp của LLM. Hướng tiếp cận gồm các đặc điểm:

1. Tiếp nhận yêu cầu trong hội thoại và gắn yêu cầu gốc với Task để truy vết.
2. Chỉ cung cấp cho Planner danh sách thiết bị tồn tại trong inventory và kiểm tra lại mọi `device_id` do mô hình trả về.
3. Biểu diễn kế hoạch thành các operation có thứ tự, dependency, vai trò thiết bị và chế độ truy cập `READ`/`WRITE`.
4. Tách Planner Agent, Network Agent và Analyst Agent; đặt lifecycle và business rule trong Orchestrator cùng domain service.
5. Yêu cầu phê duyệt thao tác `WRITE`; đối chiếu snapshot câu lệnh và SHA-256 hash trước khi thực thi.
6. Mã hóa credential thiết bị trong PostgreSQL và chỉ giải mã theo nhu cầu tại ranh giới kết nối.
7. Lưu trạng thái Task, operation, mapping thiết bị, execution, action log và activity timeline.

Đề tài chưa giải quyết đầy đủ intent assurance, tự động rollback, telemetry liên tục và đánh giá định lượng trên tập sự cố chuẩn. Do đó, đóng góp hiện tại tập trung vào kiến trúc nguyên mẫu có kiểm soát và có khả năng truy vết.

---

# CHƯƠNG 2. CƠ SỞ LÝ THUYẾT VÀ CÔNG NGHỆ

## 2.1. Large Language Model

LLM là mô hình học sâu được huấn luyện trên tập dữ liệu văn bản lớn để ước lượng phân bố xác suất của token tiếp theo. Nhờ học các mẫu ngôn ngữ và biểu diễn ngữ nghĩa, LLM có thể thực hiện nhiều tác vụ như phân loại ý định, trích xuất thực thể, sinh nội dung có cấu trúc và tổng hợp thông tin. Trong đề tài, LLM không được huấn luyện lại mà được truy cập qua NVIDIA API bằng `ChatNVIDIA`.

Hai tác vụ sử dụng LLM là lập kế hoạch và phân tích kết quả. Planner nhận yêu cầu, public inventory và JSON Schema của `ExecutionPlanCreate`; đầu ra được Pydantic kiểm tra. Khi JSON không hợp lệ, tác tử cung cấp lỗi validation để mô hình sửa, tối đa hai lần thử lại; lời gọi có timeout 90 giây. Analyst nhận danh sách kết quả thực thi đã cấu trúc và trả về `summary`, `findings`, `likely_causes`, `recommendations` cùng cờ `requires_more_data`.

Các tham số được đặt theo hướng giảm biến thiên: `temperature=0` và tắt chế độ suy luận mở rộng của model trong adapter hiện dùng. Dù vậy, tính xác định tuyệt đối không được bảo đảm. Schema validation chỉ chứng minh đúng cấu trúc, không chứng minh lệnh mạng đúng ngữ nghĩa. Vì vậy, đầu ra LLM tiếp tục phải chịu kiểm tra inventory, dependency, access mode và approval.

## 2.2. AI Agent và Multi-Agent System

AI Agent là thành phần nhận quan sát, lựa chọn hành động và tạo kết quả nhằm đạt mục tiêu trong một môi trường. Một agent thực dụng thường gồm mô hình ra quyết định, trạng thái hoặc ngữ cảnh, công cụ tương tác và cơ chế phản hồi. MAS là tập hợp nhiều agent phối hợp thông qua giao diện hoặc giao thức chung.

Trong đề tài, khái niệm “agent” được sử dụng theo vai trò ứng dụng:

- **Planner Agent:** dùng LLM để tạo execution plan có cấu trúc.
- **Network Agent:** không dùng LLM; kiểm tra tham số và gọi Network Tool.
- **Analyst Agent:** dùng LLM để phân tích output và tạo phản hồi tiếng Việt.

LangGraph phụ trách chuyển bước cấp cao; ba handler planning, execution và analysis thực hiện quy tắc của từng node. Các handler không được xem là tác tử LLM mà là thành phần phần mềm tất định. Thiết kế này tránh dùng một “siêu tác tử” vừa suy luận, giữ credential, thực thi và tự xác nhận kết quả.

## 2.3. Intent-Based Networking

RFC 9315 định nghĩa intent là tập mục tiêu vận hành và kết quả mong muốn được mô tả theo cách khai báo, không chỉ định cách đạt được [1]. IBN bao gồm hai nhóm chức năng: intent fulfillment chuyển intent thành hành động; intent assurance quan sát và xác nhận mạng tiếp tục tuân thủ intent.

Đề tài hỗ trợ một phần của intent fulfillment: người dùng nhập yêu cầu tiếng Việt, Planner biến yêu cầu thành operation và command, sau đó Orchestrator thực thi theo điều kiện. Tuy nhiên, không phải mọi câu lệnh ngôn ngữ tự nhiên đều là intent đúng nghĩa. Yêu cầu “chạy `show ip route` trên P1” là chỉ thị thao tác cụ thể, còn yêu cầu “duy trì kết nối giữa hai site khi một đường truyền lỗi” gần với intent vì mô tả kết quả mong muốn. Phiên bản hiện tại chưa có mô hình trạng thái mong muốn bền vững, phát hiện intent drift hoặc vòng assurance liên tục; do đó hệ thống chỉ mới tiếp cận IBN ở lớp giao diện và phân rã yêu cầu.

## 2.4. Network Automation

Network Automation là việc sử dụng phần mềm để thực hiện có kiểm soát các tác vụ cấu hình, kiểm tra, giám sát và quản lý vòng đời mạng. Các thành phần cơ bản gồm inventory, credential management, driver kết nối, task runner, orchestration, validation và audit.

Trong hệ thống, inventory được lưu ở PostgreSQL; thiết bị liên kết với brand, category và credential. Network Tool sử dụng `device_type` để chọn driver Netmiko. Operation được thực thi theo `display_order` và dependency `ON_SUCCESS` hoặc `ON_COMPLETION`. Lệnh đọc dùng `send_command`; lệnh ghi dùng `send_config_set`. Kết quả được lưu ở mức mapping thiết bị, lần thực thi và action log.

## 2.5. Network Troubleshooting và Root Cause Analysis

Troubleshooting là quy trình giảm dần không gian giả thuyết thông qua quan sát và kiểm tra. Root Cause Analysis (RCA) đi xa hơn việc xác định triệu chứng: mục tiêu là tìm nguyên nhân nền tảng có khả năng giải thích chuỗi sự kiện. Một quy trình RCA đáng tin cậy phải phân biệt dữ kiện quan sát, giả thuyết và kết luận; đồng thời nêu bằng chứng phản chứng hoặc mức độ thiếu dữ liệu.

Analyst Agent của đề tài được prompt để giữ nguyên hostname, địa chỉ IP, interface và mã lỗi; phân biệt dữ kiện với suy luận; không khẳng định nguyên nhân nếu thiếu bằng chứng. Tuy nhiên, hệ thống chưa tính điểm độ tin cậy, chưa đối chiếu với knowledge base và chưa có benchmark RCA. Vì vậy, trường `likely_causes` là danh sách nguyên nhân có khả năng, không phải chứng minh nguyên nhân gốc.

## 2.6. Các phương pháp kiểm tra và kiểm soát thực thi cấu hình

Kiểm soát cấu hình nên được áp dụng theo nhiều lớp:

1. **Kiểm tra đầu vào:** xác thực người dùng, phân quyền RBAC và kiểm tra schema.
2. **Giới hạn phạm vi:** chỉ cho Planner sử dụng thiết bị từ inventory; `SOURCE` và `CONTEXT` chỉ được `READ`.
3. **Kiểm tra kế hoạch:** dependency chỉ tham chiếu operation đứng trước; không cho phép device trùng trong một operation; operation có device phải có command.
4. **Kiểm tra trước thực thi:** thao tác `WRITE` phải có approval; câu lệnh thực tế phải khớp `commands_snapshot` và `request_hash` đã phê duyệt.
5. **Kiểm tra bởi thiết bị hoặc giao thức:** NETCONF định nghĩa khả năng `validate`, `test-only` và confirmed commit để giảm rủi ro trước khi áp dụng [3]. Phiên bản hiện tại của đề tài sử dụng CLI qua Netmiko/Nornir nên chưa có các bảo đảm giao dịch này.
6. **Kiểm tra hậu điều kiện:** chạy lệnh xác minh sau thay đổi và so sánh trạng thái thực tế với mục tiêu. Planner được hướng dẫn tách bước xác minh, nhưng hệ thống chưa có bộ kiểm chứng ngữ nghĩa độc lập bắt buộc cho mọi cấu hình.
7. **Khôi phục:** tạo checkpoint, rollback hoặc cấu hình ngược khi xác minh thất bại. Cơ chế này chưa được triển khai.

Ngoài ra, credential được mã hóa đối xứng bằng `pgcrypto` với AES-256. Public API chỉ trả metadata; password và enable secret chỉ được giải mã trong bộ nhớ khi chuẩn bị kết nối. Agent LLM không nhận khóa mã hóa hoặc credential.

## 2.7. LangGraph

LangGraph là thư viện xây dựng workflow tác tử theo mô hình đồ thị trạng thái. Mỗi node thực hiện một bước xử lý và trả phần state cần cập nhật; edge quy định thứ tự chuyển bước. Trong đề tài, LangGraph sở hữu luồng cấp cao `check_gns3 → plan → execute → analyze`.

Hệ thống biên dịch hai graph. Graph message mới thực hiện đầy đủ bốn bước; graph approval đi vào `execute → analyze` sau khi khôi phục Task bằng `operation_device_id`. Cách tách điểm vào phù hợp với đặc tính chờ phê duyệt kéo dài. Graph không sử dụng checkpointer làm nguồn trạng thái nghiệp vụ độc lập: Task, Operation, mapping, Approval và audit vẫn được lưu bởi domain service trong PostgreSQL. Thiết kế này tránh sai lệch giữa checkpoint và trạng thái đã được phê duyệt.

## 2.8. Netmiko và Nornir

**Netmiko** là thư viện Python chuẩn hóa việc kết nối CLI tới thiết bị mạng đa nhà cung cấp. API cung cấp các phương thức như `send_command` cho lệnh quan sát và `send_config_set` cho tập lệnh cấu hình [11]. Backend `NetmikoNetworkTool` của đề tài mở kết nối theo device config, thực thi tuần tự và luôn gọi `disconnect()` trong khối `finally`.

**Nornir** là framework tự động hóa thuần Python có inventory, task và runner dạng plugin. `ThreadedRunner` cho phép thực thi task trên nhiều host bằng nhóm luồng [12]. Trong đề tài, `NornirNetworkTool` tạo inventory động trong bộ nhớ từ PostgreSQL và sử dụng plugin `nornir-netmiko`; không tạo tệp YAML chứa secret. Backend được lựa chọn bằng biến `NETWORK_BACKEND`. Tuy nhiên, Orchestrator hiện duyệt mapping thiết bị tuần tự, và mỗi lần gọi tool chỉ tạo inventory cho một thiết bị; vì vậy lợi ích song song hóa nhiều thiết bị của Nornir chưa được khai thác đầy đủ.

## 2.9. GNS3 và GNS3 API

GNS3 là nền tảng mô phỏng/emulation mạng cho phép xây dựng topology gồm router, switch, máy ảo và các liên kết. Kiến trúc GNS3 có controller quản lý project, compute và cung cấp REST API cho backend [13]. Đây là môi trường phù hợp để kiểm thử thay đổi mạng mà không tác động hạ tầng sản xuất.

Trong đề tài, các node Cisco IOS trong GNS3 được tiếp cận qua các cổng console/Telnet được ánh xạ tới máy host. Cấu hình có `GNS3_IP`, `GNS3_PORT` và `GNS3_PROJECT_ID`. Tuy nhiên, provider hiện chỉ gọi `GET /v2/version` để xác nhận GNS3 Server khả dụng trước khi chạy workflow. Hệ thống chưa sử dụng API để đọc node/link, mở project, bật/tắt node hoặc đồng bộ topology. Inventory vận hành hiện được quản lý trong PostgreSQL.

---

# CHƯƠNG 3. PHÂN TÍCH, THIẾT KẾ VÀ XÂY DỰNG HỆ THỐNG

## 3.1. Phân tích yêu cầu hệ thống

### 3.1.1. Yêu cầu chức năng

Hệ thống được xác định với các nhóm yêu cầu chức năng sau:

- Xác thực bằng access token và refresh token; quản lý phiên và đăng xuất.
- Phân quyền theo vai trò, chức năng quản lý và hành động `View`, `Add`, `Edit`, `Delete`, `Execute`, `Approve`.
- Quản lý người dùng, vai trò, brand, category, thiết bị và credential.
- Tạo conversation khi người dùng gửi message đầu tiên; lưu lịch sử hội thoại.
- Chuyển message của người dùng thành Task và execution plan.
- Thực thi lệnh đọc hoặc cấu hình trên thiết bị đã được gán.
- Yêu cầu người có quyền phê duyệt thao tác `WRITE` trước khi kết nối thiết bị.
- Theo dõi activity timeline, trạng thái Task/operation/device và nhật ký hành động.
- Phân tích output và trả phản hồi cuối trong conversation.

### 3.1.2. Yêu cầu phi chức năng

- **An toàn:** không đưa credential vào prompt, log hoặc response; không thực thi `WRITE` khi chưa được duyệt.
- **Khả năng truy vết:** giữ quan hệ từ message tới Task, operation, execution và action log.
- **Tính toàn vẹn:** lưu execution plan trong một transaction; kiểm tra device ID và dependency.
- **Khả năng bảo trì:** tổ chức theo domain service; Agent không truy cập repository/ORM trực tiếp.
- **Khả năng mở rộng:** Network Agent phụ thuộc vào giao diện `NetworkTool`, cho phép thay Netmiko bằng Nornir.
- **Khả dụng giao diện:** cung cấp REST API và giao diện web cho hội thoại, tác vụ, inventory, audit và phân quyền.

## 3.2. Kiến trúc tổng thể hệ thống

Hệ thống áp dụng kiến trúc nhiều lớp và phân chia theo miền nghiệp vụ. LangGraph quản lý chuyển bước cấp cao, còn handler và domain service thực hiện quy tắc nghiệp vụ. Luồng tổng thể như sau:

```text
Người dùng
   │
   ▼
React/TypeScript Web UI
   │ HTTPS/REST + JWT
   ▼
FastAPI Router
   ├── Identity/RBAC
   ├── Conversation
   ├── Inventory
   └── Execution
          │
          ▼
LangGraph: check_gns3 → plan → execute → analyze
   │            │            │
Planner       Network      Analyst
 Agent         Agent        Agent
   │            │            │
NVIDIA LLM   NetworkTool   NVIDIA LLM
                │
         Netmiko hoặc Nornir
                │
           Thiết bị GNS3

PostgreSQL lưu inventory, credential mã hóa, RBAC,
conversation, kế hoạch, trạng thái, approval và audit.
```

Backend gồm các domain `identity`, `inventory`, `conversation`, `execution` và `evaluation`. Router chỉ xử lý biên HTTP; service chứa quy tắc nghiệp vụ; repository chịu trách nhiệm lưu trữ; provider che giấu chi tiết hạ tầng. Agent layer gọi public service thay vì truy cập cơ sở dữ liệu trực tiếp.

## 3.3. Thiết kế kiến trúc Multi-Agent

Kiến trúc tác tử được thiết kế theo nguyên tắc đặc quyền tối thiểu:

| Thành phần | Đầu vào | Đầu ra | Quyền bị loại trừ |
| --- | --- | --- | --- |
| Planner Agent | Message, public device inventory, JSON Schema | `ExecutionPlanCreate` | Không đọc credential, không kết nối thiết bị, không ghi DB |
| Network Agent | Operation và `TaskOperationDevice` | `NetworkExecutionResult` | Không dùng LLM, không tự chọn thiết bị, không phân tích mục tiêu |
| Analyst Agent | Danh sách kết quả thực thi | `AnalysisResult` | Không chạy command, không sửa cấu hình |
| Planning Orchestrator | Conversation và USER message | TaskDetail đã có kế hoạch | Không trực tiếp kết nối thiết bị |
| Execution Orchestrator | TaskDetail | Kết quả từng mapping và trạng thái cuối | Không tự sinh câu lệnh mới |
| Analysis Orchestrator | Task và output | Message phản hồi | Không thay đổi thiết bị |

Thiết kế không sử dụng `BaseAgent` chung hoặc agent registry. Mỗi agent có contract riêng để tránh trừu tượng hóa không cần thiết. Đây là MAS theo mô hình phối hợp qua Orchestrator, không phải nhóm agent tự do hội thoại với nhau.

## 3.4. Vai trò và cơ chế điều phối giữa các Agent

Planning Orchestrator tạo Task, ghi activity, lấy inventory và gọi Planner. Kế hoạch trả về được kiểm tra device ID trước khi lưu. Execution Orchestrator sắp xếp operation theo `display_order`, đánh giá dependency, thực thi các mapping đủ điều kiện và tổng hợp trạng thái. Khi gặp `WAITING_APPROVAL`, Orchestrator dừng Task ở trạng thái `RUNNING` và không đánh dấu sai các bước sau là thất bại. Sau quyết định phê duyệt, workflow được tiếp tục từ dữ liệu đã lưu; operation đã hoàn tất không được gửi lại.

Analysis Orchestrator chỉ chạy sau execution hoặc tạo thông báo chờ phê duyệt. Khi Task kết thúc, Analyst phân tích output và Orchestrator lưu message `AGENT/FINAL_RESPONSE`. Cơ chế điều phối là tuần tự ở cấp operation. Dependency `ON_SUCCESS` yêu cầu bước trước thành công; `ON_COMPLETION` cho phép tiếp tục khi bước trước đã kết thúc. Kế hoạch được giới hạn là DAG bằng quy tắc dependency chỉ được tham chiếu tới operation đứng trước.

## 3.5. Cơ chế quản lý thiết bị và topology

Inventory lưu các thực thể `brands`, `categories`, `credentials` và `devices`. Mỗi Device có hostname, host, port, `device_type`, location và liên kết tới credential. Brand quy định danh sách driver hỗ trợ; service kiểm tra driver khi tạo hoặc cập nhật thiết bị.

Credential được tách khỏi Device để có thể tái sử dụng và thay đổi độc lập. Password và secret được mã hóa trong PostgreSQL bằng `pgp_sym_encrypt`; khóa mã hóa chỉ lấy từ biến môi trường. Khi thực thi, `DeviceConfigRepository` join Device với Credential và giải mã theo nhu cầu. Public schema không chứa password hoặc ciphertext.

Topology logic hiện chưa được biểu diễn bằng bảng node-link riêng. Quan hệ vật lý và logic của lab được mô tả trong cấu hình GNS3, còn backend chỉ lưu danh sách endpoint quản trị. Vì vậy Planner biết các thiết bị khả dụng nhưng không được cung cấp đồ thị liên kết mạng. Đây là giới hạn đáng kể đối với suy luận đường đi và RCA dựa trên topology.

## 3.6. Quy trình tiếp nhận và phân tích yêu cầu

Quy trình đối với message đầu tiên:

1. Frontend gọi `POST /api/v1/conversations/messages` cùng Bearer token.
2. Backend kiểm tra quyền `Chatbot/Add` và lấy `user_id` từ phiên xác thực.
3. Conversation và `USER_REQUEST` đầu tiên được tạo trong một transaction.
4. HTTP response được trả; workflow AI chạy dưới dạng background task.
5. Provider kiểm tra GNS3 Server qua `/v2/version`.
6. Planning Orchestrator tạo Task, lấy inventory và gọi Planner.
7. Pydantic kiểm tra JSON; Orchestrator từ chối device ID ngoài inventory.
8. Task, operations, dependencies và mappings được lưu nguyên tử.
9. Execution Orchestrator chạy các bước đủ điều kiện.
10. Analyst tạo phản hồi cuối hoặc thông báo chờ phê duyệt.

Chỉ message có `sender_by=USER` kích hoạt workflow, nhờ đó phản hồi của Agent không tự sinh Task mới. Title conversation được tạo bằng LLM sau workflow đầu tiên và có fallback nếu lời gọi thất bại.

## 3.7. Quy trình chẩn đoán và khắc phục sự cố

Đối với yêu cầu chẩn đoán, Planner có thể tạo các operation `READ` để thu thập bảng định tuyến, trạng thái interface hoặc neighbor. Network Agent thực thi trên từng thiết bị và trả output. Analyst tổng hợp bằng chứng, phát hiện, nguyên nhân có khả năng và khuyến nghị. Nếu kế hoạch bao gồm thay đổi, operation `WRITE` phải phụ thuộc các bước kiểm tra trước đó và chờ phê duyệt.

Quy trình hiện tại chưa phải vòng khắc phục tự trị. Analyst không tạo kế hoạch mới từ kết luận RCA; hệ thống không tự quyết định rollback; cũng chưa có cơ chế lặp thu thập dữ liệu cho tới khi đủ bằng chứng. Thao tác khắc phục chỉ xảy ra nếu Planner đã đưa operation `WRITE` vào kế hoạch ban đầu và người dùng phê duyệt. Do đó, hệ thống hỗ trợ chuỗi “thu thập — phân tích — thay đổi có phê duyệt”, nhưng chưa hiện thực đầy đủ closed-loop self-healing.

## 3.8. Cơ chế kiểm tra và Human-in-the-loop

Human-in-the-loop được áp dụng tại ranh giới `WRITE`. Nếu chưa có approval, Execution Orchestrator tạo một bản ghi `PENDING` gồm mức rủi ro, lý do, snapshot câu lệnh và hash yêu cầu; mapping chuyển sang `WAITING_APPROVAL` và không mở kết nối. Người có quyền `Task Management/Approve` có thể chọn `APPROVED` hoặc `REJECTED` một lần.

Trước khi chạy cấu hình đã duyệt, Orchestrator tái tạo SHA-256 từ `operation_device_id` và danh sách command theo canonical JSON. Nếu snapshot hoặc hash không khớp, mapping chuyển `FAILED`. Cơ chế này ngăn tình huống nội dung command bị thay đổi sau khi phê duyệt. Khi bị từ chối hoặc hết hạn, cấu hình không được gửi tới thiết bị.

Mỗi giai đoạn tạo activity event; mỗi lần gọi Agent tạo `task_executions`; command thực sự có kết quả tạo `device_action_logs`. Cơ chế audit giúp phân biệt kế hoạch dự kiến với hành động đã thực hiện.

## 3.9. Thiết kế giao diện và triển khai hệ thống

Frontend được xây dựng bằng React 19, TypeScript, Vite, Tailwind CSS, TanStack Query/Table, Zustand, React Hook Form và Zod. Các màn hình gồm đăng nhập, dashboard, chatbot, task, device, credential, device catalog, audit log, user, access control, settings và profile. Route nghiệp vụ được bảo vệ; người dùng chưa có phiên được chuyển tới `/login`; đường dẫn không tồn tại hiển thị trang 404.

Mã frontend được tổ chức theo feature, mỗi feature tách component, hook, type, constant, mock và utility. Một số luồng như xác thực, device inventory, user/profile và chatbot đã có lớp gọi REST API; một số màn hình vẫn sử dụng dữ liệu mẫu. Vì vậy giao diện hiện ở trạng thái tích hợp từng phần, chưa thể xem toàn bộ dashboard là phản ánh dữ liệu runtime từ backend.

Backend chạy bằng FastAPI; PostgreSQL 17 lưu dữ liệu và dùng extension `pgcrypto`; pgAdmin hỗ trợ quản trị. Docker Compose định nghĩa các dịch vụ `api`, `db`, `migrate` và `pgadmin`. API mặc định ở cổng 8000, frontend phát triển ở cổng 5173 và PostgreSQL được ánh xạ qua cổng cấu hình. GNS3 chạy trên máy host; container API sử dụng `host.docker.internal` để truy cập GNS3 và các cổng console thiết bị.

---

# CHƯƠNG 4. THỰC NGHIỆM VÀ ĐÁNH GIÁ

## 4.1. Môi trường thực nghiệm

Môi trường được chuẩn bị trong repository gồm:

| Thành phần | Công nghệ/cấu hình |
| --- | --- |
| Backend | Python từ 3.11, FastAPI 0.137.1, Uvicorn |
| Cơ sở dữ liệu | PostgreSQL 17, SQLAlchemy, psycopg, pgcrypto |
| LLM | NVIDIA API thông qua `langchain-nvidia-ai-endpoints` |
| Thực thi mạng | Netmiko 4.7.0 hoặc Nornir 3.6.0 với `nornir-netmiko` |
| Mô phỏng mạng | GNS3 Server, Cisco IOS, console/Telnet port mapping |
| Frontend | React 19, TypeScript 6, Vite 8 |
| Đóng gói | Docker Compose cho API, database và pgAdmin |

Repository cung cấp tệp cấu hình môi trường mẫu, schema database, seed inventory và cấu hình ban đầu cho topology. Các giá trị bí mật phải được cung cấp qua biến môi trường và không được đưa vào báo cáo hoặc commit.

## 4.2. Topology và kịch bản kiểm thử

### 4.2.1. Topology

Inventory seed gồm 13 thiết bị Cisco: chín router (`P1`, `P2`, `P3`, `PE1`, `PE2`, `CE-1A`, `CE-1B`, `CE-2A`, `CE-2B`) và bốn switch (`Switch1`–`Switch4`). Các thiết bị được truy cập qua các cổng từ 5000 đến 5011; `P3` sử dụng cổng 5024.

Phần lõi sử dụng OSPF area 0 và MPLS giữa các router P/PE. `PE1` và `PE2` thiết lập MP-BGP VPNv4, hai VRF `CUS_A` và `CUS_B`, đồng thời kết nối các CE bằng eBGP. Các mạng khách hàng sử dụng các dải `172.16.x.0`; một số site chia VLAN 10 và VLAN 20 qua kết nối trunk tới switch. `P3` hiện mới có cấu hình quản trị cơ bản, phù hợp làm thiết bị mục tiêu cho các kịch bản cấu hình có kiểm soát.

### 4.2.2. Kịch bản kiểm thử

## 4.3. Tiêu chí đánh giá

Mô hình dữ liệu `task_evaluations` đã định nghĩa khung lưu kết quả đánh giá với bốn nhóm tiêu chí:

- **Goal result:** kết quả thực tế có đạt mục tiêu của yêu cầu hay không.
- **RCA result:** nguyên nhân do hệ thống dự đoán có phù hợp nguyên nhân kỳ vọng hay không.
- **Remediation result:** biện pháp khắc phục có được thực hiện và đạt hiệu quả hay không.
- **Safety result:** quá trình có tuân thủ ràng buộc an toàn hay không.

Mỗi tiêu chí có thể nhận `PASS`, `FAIL`, `UNKNOWN` hoặc `NOT_APPLICABLE`; đánh giá có thể do hệ thống hoặc con người thực hiện. Bằng chứng cần lưu trong `evaluation_evidence`. Với phép đo định lượng trong tương lai, nên bổ sung: tỷ lệ kế hoạch hợp lệ, tỷ lệ command thành công, độ chính xác RCA, tỷ lệ khắc phục thành công, số thao tác ghi bị chặn đúng, thời gian planning/execution/analysis, và tỷ lệ cần can thiệp thủ công. Hiện repository chưa có evaluator service, benchmark runner hoặc tập ground truth để tính các chỉ số này.

## 4.4. Kết quả thực nghiệm cấu hình mạng

## 4.5. Kết quả chẩn đoán sự cố

## 4.6. Kết quả khắc phục sự cố

## 4.7. Đánh giá độ an toàn và thời gian thực thi

## 4.8. Phân tích các trường hợp thất bại

## 4.9. Nhận xét và thảo luận kết quả

---

# CHƯƠNG 5. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

## 5.1. Kết quả đạt được

Đề tài đã xây dựng được nền tảng nguyên mẫu có các thành phần chính sau:

1. Backend theo miền nghiệp vụ với API xác thực, RBAC, inventory, conversation, task, operation và approval.
2. Kiến trúc nhiều tác tử gồm Planner, Network và Analyst Agent, cùng ba Orchestrator tách biệt.
3. Luồng chuyển yêu cầu tiếng Việt thành execution plan có schema, DAG dependency và device mapping.
4. Hai backend thực thi Netmiko và Nornir sử dụng chung `NetworkTool` contract.
5. Cơ chế bảo vệ thao tác ghi bằng approval, snapshot và request hash.
6. Cơ chế mã hóa credential, giải mã theo nhu cầu và không truyền bí mật cho LLM.
7. Hệ thống trạng thái và audit gồm activity event, task execution và device action log.
8. Giao diện web theo feature cho các chức năng quản trị và hội thoại; một số luồng đã kết nối backend.
9. Môi trường GNS3 cùng inventory 13 thiết bị phục vụ phát triển và kiểm thử.

Các kết quả trên chứng minh tính khả thi về mặt kiến trúc của việc kết hợp LLM với công cụ tự động hóa mạng trong một quy trình có ranh giới kiểm soát. Tuy nhiên, do chưa có dữ liệu thực nghiệm định lượng, báo cáo không kết luận về độ chính xác, độ an toàn thực tế hoặc hiệu năng end-to-end.

## 5.2. Hạn chế của đề tài

- LangGraph đã điều phối luồng cấp cao nhưng chưa dùng persistent checkpointer; việc resume dựa trên business state trong PostgreSQL.
- GNS3 API mới chỉ dùng để kiểm tra `/v2/version`, chưa đồng bộ node, link và trạng thái topology.
- Planner không nhận đồ thị topology, telemetry liên tục hoặc cơ sở tri thức cấu hình.
- Validation hiện chủ yếu ở mức schema, inventory, dependency và approval; chưa có parser cú pháp theo vendor, dry-run, candidate datastore, confirmed commit hoặc rollback tự động.
- Analyst tạo nguyên nhân có khả năng nhưng chưa được grounding bằng knowledge base và chưa được đánh giá trên tập RCA có ground truth.
- Quy trình chưa tự lặp sau phân tích và chưa phải closed-loop self-healing.
- Nornir được triển khai nhưng lợi ích chạy song song nhiều thiết bị chưa được khai thác đầy đủ do Orchestrator xử lý mapping tuần tự.
- Frontend còn kết hợp dữ liệu thật và mock data; một số màn hình quản trị chưa phản ánh hoàn toàn trạng thái backend.
- Chưa có evaluator service và chưa có kết quả trong các mục thực nghiệm 4.4–4.9.
- Sau khi tích hợp LangGraph, nhóm kiểm thử nhanh `tests/agents`, `tests/core` và `tests/test_api.py` có 20 ca đạt. Bộ kiểm thử tích hợp đầy đủ còn phụ thuộc hạ tầng và chưa được xác nhận hoàn tất trong lần lập báo cáo này.

## 5.3. Hướng phát triển trong tương lai

Các hướng phát triển ưu tiên gồm:

1. Xây dựng bộ kịch bản thực nghiệm có ground truth cho cấu hình, chẩn đoán, RCA và remediation; tự động ghi `task_evaluations`.
2. Bổ sung bộ kiểm tra command theo vendor, pre-check/post-check bắt buộc, backup cấu hình, rollback và cơ chế giao dịch khi nền tảng hỗ trợ.
3. Đồng bộ topology từ GNS3 API, biểu diễn node-link trong database và cung cấp topology tối thiểu cho Planner/Analyst.
4. Thu thập telemetry, syslog và trạng thái giao thức; xây dựng kho bằng chứng để giảm hallucination trong RCA.
5. Thiết kế vòng lặp có giới hạn cho phép Analyst yêu cầu thêm dữ liệu nhưng không tự mở rộng quyền ghi.
6. Khai thác Nornir cho thực thi song song có kiểm soát, giới hạn concurrency và chính sách dừng theo miền lỗi.
7. Hoàn thiện tích hợp frontend-backend, thay mock data bằng API và hiển thị đầy đủ approval, timeline cùng bằng chứng đánh giá.
8. Khắc phục test double, tách unit/integration/end-to-end test và chạy pipeline kiểm thử tái lập trong CI.
9. Mở rộng LangGraph bằng nhánh thu thập bổ sung và vòng chẩn đoán có giới hạn; chỉ bổ sung persistent checkpointer khi đã xác định rõ cơ chế đồng bộ với business state.
10. Đánh giá bảo mật chuyên sâu: phân quyền theo phạm vi thiết bị, quản lý secret bằng secret manager, giới hạn command, chống prompt injection và kiểm thử khả năng lạm dụng approval.

---

# TÀI LIỆU THAM KHẢO

[1] A. Clemm, L. Ciavaglia, L. Z. Granville, J. Tantsura, “Intent-Based Networking — Concepts and Definitions,” RFC 9315, 2022. https://www.rfc-editor.org/rfc/rfc9315.html

[2] Q. Wu, M. Boucadair, D. Lopez, C. Xie, L. Geng, “A Framework for Automating Service and Network Management with YANG,” RFC 8969, 2021. https://www.rfc-editor.org/rfc/rfc8969.html

[3] R. Enns, M. Bjorklund, J. Schoenwaelder, A. Bierman, “Network Configuration Protocol (NETCONF),” RFC 6241, 2011. https://www.rfc-editor.org/rfc/rfc6241.html

[4] S. Yao et al., “ReAct: Synergizing Reasoning and Acting in Language Models,” ICLR, 2023. https://arxiv.org/abs/2210.03629

[5] Q. Wu et al., “AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation,” 2023. https://arxiv.org/abs/2308.08155

[6] C. Wang, M. Scazzariello, A. Farshin, D. Kostić, M. Chiesa, “Making Network Configuration Human Friendly,” 2023. https://arxiv.org/abs/2309.06342

[7] O. G. Lira, O. M. Caicedo, N. L. S. da Fonseca, “Large Language Models for Zero Touch Network Configuration Management,” 2024. https://arxiv.org/abs/2408.13298

[8] Y. Wei et al., “Leveraging LLM Agents for Translating Network Configurations,” 2025. https://arxiv.org/abs/2501.08760

[9] H. Song et al., “Network Telemetry Framework,” RFC 9232, 2022. https://www.rfc-editor.org/rfc/rfc9232.html

[10] H. Zhou et al., “Large Language Models (LLMs) for Telecom Root Cause Analysis (RCA): A Structured Reasoning Framework for Evidence-Grounded Diagnosis,” 2026. https://arxiv.org/abs/2609.02805

[11] Netmiko Project, “Netmiko API Documentation.” https://ktbyers.github.io/netmiko/docs/netmiko/

[12] Nornir Project, “Nornir 3.6.0 Documentation — Plugins and Runners.” https://nornir.readthedocs.io/en/v3.6.0/plugins/

[13] GNS3 Project, “GNS3 Architecture Documentation.” https://docs.gns3.com/docs/using-gns3/design/architecture

*Ngày đối chiếu tài liệu và mã nguồn: 31/10/2026.*
