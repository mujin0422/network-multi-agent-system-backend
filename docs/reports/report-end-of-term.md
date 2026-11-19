# BÁO CÁO CUỐI KỲ ĐỒ ÁN CHUYÊN NGÀNH

## NGHIÊN CỨU VÀ XÂY DỰNG HỆ THỐNG MULTI-AGENT HỖ TRỢ CẤU HÌNH VÀ XỬ LÝ SỰ CỐ MẠNG

**Trường:** Đại học Sài Gòn — Chuyên ngành Kỹ thuật máy tính  
**Nhóm sinh viên:** Phạm Đăng Minh Khang; Phạm Đình Duy Thái; Triệu Phú Quân  
**Phạm vi đối chiếu:** mã nguồn nhánh `develop` của backend (commit `5e9f0815a0`, 18/11/2026) và frontend (commit `d96e94f197`, 19/11/2026). Dữ liệu benchmark lịch sử trong Chương 4 chưa được chạy lại trên các commit này.

### TÓM TẮT ĐỀ TÀI

Đề tài “Nghiên cứu và xây dựng hệ thống Multi-Agent hỗ trợ cấu hình và xử lý sự cố mạng” nhằm nghiên cứu và ứng dụng mô hình ngôn ngữ lớn (Large Language Model) kết hợp kiến trúc đa tác nhân (Multi-Agent System) trong tự động hóa quản trị mạng.

Hệ thống được thiết kế với bốn tác nhân chuyên trách: Planner Agent phân tích yêu cầu và lập kế hoạch nghiệp vụ; Configuration Agent chuyển yêu cầu thay đổi thành câu lệnh CLI; Network Agent thực thi các tác vụ đã được kiểm soát trên thiết bị mạng; Analyst Agent phân tích bằng chứng và hỗ trợ xác định nguyên nhân sự cố. Quá trình phối hợp được điều phối thông qua LangGraph, kết hợp Netmiko và Nornir để tương tác với thiết bị trong môi trường giả lập GNS3. Đồng thời, cơ chế phê duyệt Human-in-the-loop được tích hợp nhằm kiểm soát các thao tác thay đổi cấu hình.

Đề tài xây dựng bộ kịch bản thực nghiệm để đánh giá tỷ lệ hoàn thành nhiệm vụ, khả năng xác định nguyên nhân gốc và thời gian thực thi. Kết quả nghiên cứu góp phần làm rõ khả năng ứng dụng kiến trúc Multi-Agent trong hỗ trợ quản trị mạng, đồng thời tạo cơ sở cho việc tiếp tục hoàn thiện hệ thống.

# MỞ ĐẦU

## Lý do chọn đề tài

Trong những năm gần đây, sự phát triển của các hệ thống mạng về quy mô, số lượng thiết bị, giao thức và dịch vụ đã làm gia tăng mức độ phức tạp của công tác quản trị và vận hành mạng. Bên cạnh các thiết bị mạng truyền thống, việc ứng dụng công nghệ ảo hóa và các kiến trúc mạng hiện đại đặt ra yêu cầu ngày càng cao đối với khả năng cấu hình, giám sát và xử lý sự cố. Trong thực tế, quản trị viên thường phải thực hiện nhiều công việc liên tiếp như kiểm tra trạng thái thiết bị, thu thập thông tin vận hành, phân tích nguyên nhân sự cố, lựa chọn phương án khắc phục và xác minh kết quả. Những công việc này đòi hỏi kiến thức chuyên môn, kinh nghiệm và có thể tiêu tốn nhiều thời gian, đặc biệt trong các môi trường mạng có nhiều thiết bị và cấu hình phức tạp [1], [8].

Trước những thách thức đó, các phương pháp ứng dụng trí tuệ nhân tạo trong quản lý và vận hành mạng đã nhận được nhiều sự quan tâm. Đặc biệt, sự phát triển của mô hình Large Language Model (LLM) mở ra khả năng hỗ trợ quản trị mạng thông qua giao tiếp bằng ngôn ngữ tự nhiên. Khác với nhiều phương pháp Machine Learning truyền thống được phát triển cho các nhiệm vụ cụ thể, LLM có khả năng xử lý và kết hợp các nguồn thông tin dạng văn bản như tài liệu kỹ thuật, tệp cấu hình, nhật ký hệ thống và kết quả thực thi lệnh. Theo khảo sát của Hong và cộng sự [1], LLM có thể được ứng dụng trong nhiều nhiệm vụ quản lý mạng, bao gồm thiết kế mạng, cấu hình, quản lý sự cố, bảo mật và điều phối hoạt động mạng.

Tuy nhiên, việc ứng dụng LLM vào các tác vụ cấu hình và xử lý sự cố mạng vẫn tồn tại những thách thức về độ tin cậy và an toàn. Một trong những hạn chế đáng chú ý là hiện tượng hallucination, khi mô hình có thể đưa ra thông tin hoặc đề xuất cấu hình không chính xác. Trong môi trường mạng, việc thực thi những thay đổi không phù hợp có thể ảnh hưởng đến khả năng kết nối và hoạt động của các thiết bị. Vì vậy, các hệ thống tự động hóa dựa trên LLM cần có cơ chế kiểm tra tính hợp lệ của hành động, xác minh trạng thái mạng và kiểm soát quá trình thực thi [1], [2].

Các nghiên cứu gần đây đã tiếp cận vấn đề này theo những hướng khác nhau. LLM-NetCFG [2] nghiên cứu khả năng chuyển yêu cầu bằng ngôn ngữ tự nhiên thành cấu hình mạng và thực hiện xác minh cấu hình. NetConfArena [5] đề xuất môi trường đánh giá cho AI Agent trong bài toán cấu hình mạng theo cơ chế tương tác vòng kín, trong đó agent có thể quan sát trạng thái, thực hiện hành động và kiểm tra kết quả. Trong lĩnh vực xử lý sự cố mạng, NIKA [3] cung cấp môi trường đánh giá khả năng phát hiện, định vị và xác định nguyên nhân gốc của sự cố. Bên cạnh đó, NETARENA [4] nhấn mạnh sự cần thiết của việc đánh giá AI Agent dựa trên tính đúng đắn, độ an toàn và thời gian thực thi.

Một hướng tiếp cận khác là kiến trúc hệ thống đa tác tử (Multi-Agent System), trong đó các nhiệm vụ phức tạp được phân chia cho những agent có vai trò chuyên biệt. OpsAgent [6] là một ví dụ về việc ứng dụng Multi-Agent trong quản lý sự cố của hệ thống microservice, sử dụng cơ chế điều phối và kiểm tra chéo giữa các agent nhằm hỗ trợ quá trình phân tích nguyên nhân sự cố. Cách tiếp cận này cung cấp cơ sở tham khảo cho việc phân chia trách nhiệm và tổ chức phối hợp giữa các thành phần trong hệ thống quản trị mạng.

Trên cơ sở các nghiên cứu đã khảo sát, đề tài lựa chọn nghiên cứu khả năng tổ chức và phối hợp nhiều AI Agent trong một hệ thống hỗ trợ cấu hình, chẩn đoán và khắc phục sự cố mạng. Trọng tâm của đề tài là thiết kế kiến trúc Multi-Agent với các chức năng chuyên biệt, xây dựng cơ chế điều phối và tích hợp các công cụ cho phép hệ thống tương tác với thiết bị mạng trong môi trường mô phỏng.

Xuất phát từ những vấn đề trên, đề tài “Nghiên cứu và xây dựng hệ thống Multi-Agent hỗ trợ cấu hình và xử lý sự cố mạng” được lựa chọn nhằm nghiên cứu, thiết kế và xây dựng một hệ thống hỗ trợ quản trị viên thực hiện các tác vụ cấu hình, chẩn đoán và khắc phục sự cố mạng thông qua giao tiếp ngôn ngữ tự nhiên. Hệ thống được triển khai và đánh giá trong môi trường mạng mô phỏng, tập trung vào khả năng thực hiện nhiệm vụ, độ chính xác trong chẩn đoán, hiệu quả khắc phục sự cố và tính an toàn của các hành động cấu hình.

## Mục đích và nhiệm vụ nghiên cứu

### Mục đích nghiên cứu

Mục đích của đề tài là nghiên cứu, thiết kế và xây dựng một hệ thống đa tác tử (Multi-Agent System) ứng dụng mô hình ngôn ngữ lớn nhằm hỗ trợ quản trị viên mạng thực hiện các tác vụ cấu hình thiết bị, chẩn đoán và khắc phục sự cố thông qua giao tiếp bằng ngôn ngữ tự nhiên.

Hệ thống tập trung vào việc phân chia các chức năng quản trị mạng thành những agent chuyên trách, xây dựng cơ chế điều phối và phối hợp giữa các agent, đồng thời tích hợp các công cụ tự động hóa nhằm cho phép hệ thống tương tác với thiết bị mạng trong môi trường mô phỏng.

Bên cạnh đó, đề tài nghiên cứu các phương pháp kiểm tra và kiểm soát hành động cấu hình do hệ thống đề xuất, kết hợp cơ chế Human-in-the-loop để quản trị viên có thể xem xét và xác nhận trước khi thực hiện thay đổi trên thiết bị.

### Nhiệm vụ nghiên cứu

Khảo sát và phân tích các nghiên cứu liên quan đến ứng dụng Large Language Models, AI Agent, Multi-Agent System, Network Configuration Automation và Network Troubleshooting nhằm xác định hướng tiếp cận phù hợp.

Thiết kế kiến trúc Multi-Agent bao gồm các thành phần đảm nhiệm các chức năng chuyên biệt gồm tiếp nhận và điều phối yêu cầu, thu thập thông tin mạng, chẩn đoán sự cố, cấu hình và khắc phục, kiểm chứng kết quả.

Xây dựng cơ chế tương tác với các thiết bị mạng trong môi trường ảo hóa GNS3 thông qua giao diện dòng lệnh và các công cụ tự động hóa.

Áp dụng cơ chế Human-in-the-loop kết hợp với các bước kiểm tra tính hợp lệ của đề xuất cấu hình nhằm hỗ trợ kiểm soát những thay đổi được thực hiện.

Xây dựng tập kịch bản thực nghiệm có trạng thái ban đầu, yêu cầu nhiệm vụ, nguyên nhân sự cố, trạng thái cấu hình mục tiêu và các điều kiện kiểm chứng được xác định trước, nhằm phục vụ quá trình đánh giá hiệu quả của hệ thống.

Đánh giá thực nghiệm bằng các chỉ số đã triển khai gồm Task Success Rate, Detection Score, các chỉ số Precision/Recall/F1 cho Localization, Fault Type và RCA, Active Workflow Latency và Interaction Turns; đồng thời xác định Remediation Success Rate và Safety là các tiêu chí cần hoàn thiện bộ chấm trong giai đoạn tiếp theo.

## Đối tượng và phạm vi nghiên cứu

### Khách thể nghiên cứu

Khách thể nghiên cứu là các quy trình quản trị và vận hành hệ thống mạng quy mô nhỏ và vừa, bao gồm việc cấu hình thiết bị, kiểm tra trạng thái mạng, chẩn đoán nguyên nhân sự cố và thực hiện các biện pháp khắc phục.

### Đối tượng nghiên cứu

Đối tượng nghiên cứu của đề tài là kiến trúc hệ thống Multi-Agent ứng dụng mô hình ngôn ngữ lớn trong các tác vụ cấu hình, chẩn đoán và khắc phục sự cố mạng. Nghiên cứu tập trung vào phương pháp phân chia chức năng giữa các agent, cơ chế điều phối và trao đổi thông tin, phương pháp tương tác với thiết bị mạng và các cơ chế kiểm soát hành động cấu hình nhằm hỗ trợ quá trình quản trị mạng.

### Phạm vi nghiên cứu

Về không gian: Đề tài được triển khai và thử nghiệm trong môi trường mô phỏng mạng, sử dụng các thiết bị ảo hóa. Việc thực nghiệm không được thực hiện trực tiếp trên hệ thống mạng production nhằm đảm bảo tính kiểm soát và khả năng tái lập các kịch bản.

Về nội dung: đề tài giới hạn ở các sự cố mạng phổ biến tại tầng Data Link và Network trong mô hình OSI. Các tác vụ được triển khai gồm cấu hình địa chỉ IP, thay đổi trạng thái interface, cấu hình định tuyến và một số chức năng giao thức mạng trong môi trường thực nghiệm. Bộ kịch bản bao gồm interface bị shutdown, sai địa chỉ IP hoặc subnet mask, thiếu hoặc sai thông tin OSPF, OSPF area mismatch, MPLS bị vô hiệu hóa trên interface, eBGP neighbor bị shutdown, ACL chặn kết nối và một số trường hợp mất kết nối do cấu hình không phù hợp.

Về công nghệ AI: Đề tài sử dụng mô hình LLM đã được phát triển sẵn để xây dựng các AI Agent. Trọng tâm là thiết kế kiến trúc hệ thống, cơ chế phối hợp và khả năng sử dụng các công cụ tương tác với thiết bị mạng, không nghiên cứu huấn luyện một LLM mới.

## Ý nghĩa khoa học và ý nghĩa thực tiễn

### Ý nghĩa khoa học

Đề tài góp phần nghiên cứu và làm rõ khả năng ứng dụng kiến trúc Multi-Agent trong lĩnh vực quản trị mạng, đặc biệt đối với các nhiệm vụ cấu hình thiết bị, chẩn đoán nguyên nhân và hỗ trợ xử lý sự cố mạng. Thông qua việc xây dựng và đánh giá một hệ thống thực nghiệm, đề tài cung cấp thêm cơ sở tham khảo về cách tổ chức và vận hành các AI Agent trong môi trường mạng có những yêu cầu kỹ thuật và điều kiện kiểm soát cụ thể.

Thông qua quá trình phân tích, thiết kế và triển khai hệ thống, đề tài khảo sát phương pháp phân chia các chức năng quản trị mạng thành những nhiệm vụ chuyên biệt do từng AI Agent đảm nhiệm. Đồng thời, nghiên cứu xem xét cơ chế điều phối, trao đổi thông tin và phối hợp thực hiện nhiệm vụ giữa các Agent, cũng như phương pháp tích hợp mô hình ngôn ngữ lớn với những công cụ quản trị mạng nhằm hình thành một quy trình xử lý thống nhất.

Bên cạnh đó, đề tài nghiên cứu việc kết hợp các phương pháp kiểm tra tính hợp lệ, kiểm chứng kết quả và cơ chế Human-in-the-loop trong quá trình thực thi những đề xuất cấu hình do LLM tạo ra. Việc tích hợp các cơ chế này nhằm làm rõ vai trò của hoạt động kiểm soát và phê duyệt trong hệ thống tự động hóa mạng có sử dụng AI, đặc biệt đối với những thao tác có khả năng ảnh hưởng đến trạng thái hoạt động của thiết bị.

Kết quả thực nghiệm của đề tài được kỳ vọng cung cấp thêm thông tin về khả năng thực hiện nhiệm vụ, độ chính xác trong chẩn đoán, hiệu quả xử lý sự cố và mức độ tuân thủ các điều kiện an toàn của hệ thống Multi-Agent. Những kết quả này có thể được sử dụng làm cơ sở tham khảo cho các nghiên cứu tiếp theo về ứng dụng AI Agent trong tự động hóa quản trị và vận hành hệ thống mạng.

### Ý nghĩa thực tiễn

Về mặt thực tiễn, hệ thống được xây dựng hướng đến việc hỗ trợ quản trị viên mạng trong quá trình thực hiện các tác vụ cấu hình, giám sát trạng thái và xử lý sự cố thông qua giao tiếp bằng ngôn ngữ tự nhiên. Thay vì phải trực tiếp thực hiện toàn bộ các thao tác bằng dòng lệnh, người quản trị có thể mô tả yêu cầu để hệ thống phân tích, đề xuất phương án và hỗ trợ thực hiện theo quy trình được kiểm soát.

Việc tổ chức các chức năng thành những AI Agent chuyên trách tạo điều kiện phân tách nhiệm vụ và quản lý từng giai đoạn xử lý một cách rõ ràng. Cách tiếp cận này có thể hỗ trợ quá trình bảo trì, mở rộng và tích hợp thêm các chức năng quản trị mạng trong tương lai, đồng thời tạo thuận lợi cho việc theo dõi kết quả thực hiện và xác định trách nhiệm của từng thành phần trong hệ thống.

Thông qua việc tích hợp các công cụ tự động hóa với cơ chế xác nhận trước khi thực thi, hệ thống hướng đến giảm bớt những thao tác cấu hình thủ công có tính lặp lại và hỗ trợ kiểm soát các thay đổi trên thiết bị mạng. Các bước kiểm tra và phê duyệt được thiết kế nhằm giúp quản trị viên xem xét phương án xử lý trước khi áp dụng, qua đó góp phần hạn chế những rủi ro phát sinh từ cấu hình không phù hợp.

Kết quả nghiên cứu và triển khai có thể được sử dụng làm tài liệu tham khảo cho việc phát triển các hệ thống hỗ trợ quản trị mạng trong môi trường phòng thí nghiệm, phục vụ hoạt động đào tạo và nghiên cứu về AI Agent, Multi-Agent System và Network Automation. Đồng thời, hệ thống thực nghiệm có thể làm nền tảng để tiếp tục nghiên cứu khả năng mở rộng và ứng dụng trong những môi trường mạng có yêu cầu vận hành phức tạp hơn.

---

# CHƯƠNG 1. GIỚI THIỆU VÀ TỔNG QUAN TÌNH HÌNH NGHIÊN CỨU

## 1.1. Bài toán quản trị và tự động hóa mạng hiện nay

Hạ tầng mạng máy tính hiện nay ngày càng phát triển về quy mô và mức độ phức tạp, với sự kết hợp của nhiều loại thiết bị, giao thức truyền thông và công nghệ mạng khác nhau. Trong quá trình vận hành, quản trị viên phải thực hiện nhiều nhiệm vụ như cấu hình địa chỉ IP, thiết lập giao thức định tuyến, quản lý VLAN, giám sát trạng thái thiết bị và xử lý các sự cố kết nối. Những nhiệm vụ này thường có mối quan hệ phụ thuộc lẫn nhau, khiến một thay đổi cấu hình trên thiết bị có thể ảnh hưởng đến hoạt động của nhiều thành phần trong hệ thống. Theo Sidhu và Sharma [17], các phương pháp quản trị mạng truyền thống đang dần bộc lộ những hạn chế về khả năng mở rộng, tính linh hoạt và hiệu quả vận hành trước sự gia tăng về quy mô và độ phức tạp của hạ tầng mạng hiện đại.

Trong phương pháp quản trị thủ công, người vận hành thường phải truy cập trực tiếp vào từng thiết bị thông qua giao diện dòng lệnh để kiểm tra trạng thái, xác định nguyên nhân sự cố và thực hiện các thao tác cấu hình tương ứng. Quá trình này đòi hỏi kiến thức chuyên môn, khả năng phân tích và kinh nghiệm xử lý các tình huống phát sinh. Khi số lượng thiết bị tăng lên, việc thực hiện nhiều thao tác lặp lại không chỉ làm gia tăng khối lượng công việc mà còn tiềm ẩn nguy cơ sai sót, đặc biệt khi các thiết bị sử dụng những cú pháp cấu hình hoặc cơ chế quản lý khác nhau. Những hạn chế này đặt ra yêu cầu về các phương pháp quản trị có khả năng giảm sự phụ thuộc vào thao tác thủ công và nâng cao tính nhất quán trong quá trình vận hành hệ thống mạng.

Để giải quyết những khó khăn trên, tự động hóa mạng được nghiên cứu và ứng dụng nhằm hỗ trợ triển khai cấu hình, thu thập thông tin trạng thái và kiểm tra hoạt động của thiết bị thông qua các công cụ phần mềm. Nghiên cứu của Abdellatif và cộng sự [18] đã đánh giá các phương pháp tự động hóa trong những nhiệm vụ như xây dựng cấu trúc mạng, tạo cấu hình và kiểm thử, qua đó làm rõ khả năng tiết kiệm thời gian và công sức so với các phương pháp thực hiện truyền thống. Tuy nhiên, tự động hóa mạng không chỉ đơn thuần là gửi một tập lệnh đến nhiều thiết bị mà còn đòi hỏi cơ chế quản lý thông tin thiết bị, xác thực quyền truy cập, xác định thứ tự thực hiện các thao tác và kiểm chứng trạng thái hệ thống sau khi áp dụng cấu hình.

Đối với các nhiệm vụ chẩn đoán và xử lý sự cố, hệ thống cần có khả năng thu thập dữ liệu từ nhiều thiết bị, phân tích những dấu hiệu bất thường và xác định phương án khắc phục phù hợp với trạng thái mạng hiện tại. Bên cạnh đó, các thao tác thay đổi cấu hình cần được kiểm tra và kiểm soát nhằm hạn chế nguy cơ gây gián đoạn hoạt động của những thành phần khác. Vì vậy, bài toán đặt ra không chỉ là tự động hóa quá trình thực thi lệnh mà còn là xây dựng một quy trình có khả năng kết hợp giữa phân tích yêu cầu, chẩn đoán sự cố, đề xuất phương án xử lý và kiểm chứng kết quả. Đây cũng là cơ sở để nghiên cứu các hướng tiếp cận sử dụng trí tuệ nhân tạo nhằm hỗ trợ quản trị và tự động hóa mạng một cách linh hoạt, có kiểm soát và phù hợp với yêu cầu vận hành thực tế.

## 1.2. Lịch sử nghiên cứu vấn đề

### 1.2.1. Ứng dụng AI và LLM trong quản trị mạng

Việc ứng dụng trí tuệ nhân tạo trong quản lý và vận hành mạng đã được nghiên cứu nhằm hỗ trợ tự động hóa các nhiệm vụ như cấu hình thiết bị, giám sát trạng thái, phát hiện bất thường và xử lý sự cố. Các phương pháp dựa trên Machine Learning (ML), Deep Learning (DL) và Reinforcement Learning (RL) đã được áp dụng cho nhiều bài toán quản trị mạng. Tuy nhiên, các phương pháp này thường cần dữ liệu huấn luyện và cơ chế xử lý được thiết kế phù hợp với từng loại nhiệm vụ hoặc môi trường cụ thể.

Hong và cộng sự [1] thực hiện một khảo sát toàn diện về việc ứng dụng mô hình Large Language Model (LLM) trong quản lý và vận hành mạng. Các tác giả phân loại những nhiệm vụ quản trị mạng thành các nhóm chính, bao gồm thiết kế mạng, cấu hình mạng, quản lý sự cố, bảo mật và điều phối hoạt động mạng. Nghiên cứu cho thấy LLM có khả năng tiếp nhận yêu cầu bằng ngôn ngữ tự nhiên, xử lý các nguồn dữ liệu phi cấu trúc như tài liệu kỹ thuật, tệp cấu hình và nhật ký hệ thống, từ đó hỗ trợ quản trị viên trong quá trình phân tích và thực hiện các tác vụ mạng.

Bên cạnh những khả năng trên, nghiên cứu của Hong và cộng sự cũng chỉ ra các thách thức khi triển khai LLM trong môi trường mạng, bao gồm hiện tượng hallucination, hạn chế về kiến thức chuyên ngành, chi phí tính toán và các vấn đề bảo mật thông tin. Những hạn chế này đặc biệt đáng chú ý đối với các hệ thống cho phép LLM đề xuất hoặc thực hiện thay đổi cấu hình thiết bị, bởi kết quả không chính xác có thể ảnh hưởng đến hoạt động của mạng.

Ở góc độ quản lý vận hành hệ thống, Zhang và cộng sự [7] về ứng dụng LLM trong Artificial Intelligence for IT Operations (AIOps). Nghiên cứu tổng hợp và phân tích 183 công trình được công bố trong giai đoạn 2020–2024, tập trung vào các nguồn dữ liệu vận hành, nhiệm vụ quản lý sự cố, phương pháp ứng dụng LLM và cách thức đánh giá. Các nhiệm vụ được khảo sát bao gồm phát hiện bất thường, phân tích nguyên nhân gốc và hỗ trợ khắc phục sự cố.

Nhìn chung, các nghiên cứu khảo sát trên cung cấp cơ sở lý thuyết về khả năng ứng dụng LLM trong quản trị và vận hành hệ thống và cũng cho thấy nhu cầu kết hợp LLM với các công cụ tương tác môi trường và cơ chế kiểm soát phù hợp khi triển khai những tác vụ quản trị mạng có ảnh hưởng trực tiếp đến trạng thái thiết bị.

### 1.2.2. Các nghiên cứu về cấu hình mạng tự động

Cấu hình mạng là một trong những nhiệm vụ quan trọng của quá trình quản trị hệ thống. Các yêu cầu cấu hình thường được quản trị viên mô tả dưới dạng mục tiêu hoặc chính sách, trong khi việc triển khai đòi hỏi chuyển đổi những yêu cầu này thành các tham số và câu lệnh phù hợp với từng thiết bị. Do đó, việc ứng dụng LLM vào quá trình chuyển đổi yêu cầu ngôn ngữ tự nhiên thành cấu hình mạng là một hướng nghiên cứu đáng chú ý.

Lira và cộng sự [2] đã đề xuất LLM-NetCFG, một hệ thống hướng đến Zero-Touch Network Configuration Management. Hệ thống sử dụng LLM để chuyển các intent bằng ngôn ngữ tự nhiên thành cấu hình cụ thể. Kiến trúc bao gồm các thành phần chịu trách nhiệm sinh cấu hình, kiểm tra cấu hình và điều phối quá trình thực hiện. Nếu cấu hình không vượt qua quá trình xác minh, thông tin lỗi có thể được sử dụng để điều chỉnh kết quả trước khi triển khai. Cách tiếp cận này cho thấy việc sinh câu lệnh cấu hình bằng LLM chưa đủ để đảm bảo một hệ thống network automation đáng tin cậy. Kết quả do mô hình tạo ra cần được xác minh trước hoặc sau khi áp dụng trên thiết bị.

NetConfArena [5] phát triển cách tiếp cận này theo hướng tương tác vòng kín. Thay vì chỉ yêu cầu LLM sinh ra một tập lệnh cấu hình và so sánh với câu trả lời mẫu, AI Agent được đặt trong một môi trường mạng có thể thực thi. Agent quan sát trạng thái hiện tại, thực hiện cấu hình, sử dụng các lệnh kiểm tra để thu thập phản hồi và tiếp tục sửa đổi khi cần thiết. Một điểm quan trọng của NetConfArena là kết quả cuối cùng được đánh giá dựa trên hành vi của mạng thay vì chỉ dựa trên việc câu lệnh có được thiết bị chấp nhận hay không. Điều này phù hợp với thực tế rằng nhiều tập lệnh khác nhau có thể cùng tạo ra một trạng thái mạng đúng.

Từ hai nghiên cứu trên, có thể nhận thấy LLM có khả năng hỗ trợ chuyển đổi yêu cầu ngôn ngữ tự nhiên thành cấu hình thiết bị mạng. Tuy nhiên, để áp dụng trong một hệ thống quản trị mạng, quá trình cấu hình cần được kết hợp với khả năng thu thập thông tin trạng thái, kiểm tra hành động và đánh giá kết quả thực hiện. Đây là cơ sở tham khảo cho việc xây dựng chức năng lập kế hoạch và tương tác thiết bị mạng trong đề tài.

### 1.2.3. Các nghiên cứu về chẩn đoán và khắc phục sự cố mạng

Bên cạnh cấu hình thiết bị, chẩn đoán và xử lý sự cố là những nhiệm vụ quan trọng trong quá trình vận hành mạng. Khi xảy ra sự cố, quản trị viên thường phải thu thập thông tin từ nhiều thiết bị, kiểm tra trạng thái kết nối, phân tích kết quả và xác định nguyên nhân trước khi lựa chọn phương án khắc phục. Quá trình này đòi hỏi kinh nghiệm, khả năng kết hợp thông tin từ nhiều nguồn và thực hiện các bước kiểm tra phù hợp với từng tình huống.

Wang và cộng sự [3] đề xuất NIKA, một framework dùng để đánh giá AI Agent trong bài toán rong bài toán Network Troubleshooting. NIKA cung cấp các kịch bản sự cố mạng được xây dựng trên nhiều loại topology, đồng thời cho phép AI Agent tương tác với môi trường thông qua những công cụ giám sát và chẩn đoán. Nghiên cứu phân chia việc đánh giá khả năng troubleshooting thành ba nhiệm vụ chính, bao gồm: phát hiện sự cố, xác định vị trí sự cố và xác định nguyên nhân gốc.

Kết quả thực nghiệm của NIKA cho thấy các mô hình lớn có thể đạt kết quả tương đối tốt hơn ở bước phát hiện sự cố, nhưng vẫn gặp khó khăn ở bước xác định chính xác vị trí lỗi và nguyên nhân gốc. Điều này cho thấy Network Troubleshooting đòi hỏi nhiều hơn khả năng hiểu ngôn ngữ. Agent cần liên tục thu thập bằng chứng từ môi trường, lựa chọn công cụ kiểm tra thích hợp và kết hợp nhiều thông tin trước khi đưa ra kết luận.

Ở hướng nghiên cứu về đánh giá AI Agent trong tự động hóa mạng, Zhou và cộng sự [4] đề xuất NETARENA, một framework tạo benchmark động cho các nhiệm vụ quản lý và vận hành hệ thống mạng. NETARENA sử dụng mô hình trừu tượng dựa trên trạng thái và hành động để biểu diễn nhiệm vụ, trong đó agent thực hiện các thao tác trên môi trường nhằm đạt được trạng thái mục tiêu.

Khác với phương pháp đánh giá chỉ dựa trên kết quả đầu ra, NETARENA tích hợp với các môi trường thực thi để đánh giá hành vi của agent thông qua ba tiêu chí chính: tính đúng đắn, độ an toàn và thời gian thực hiện . Nghiên cứu chỉ ra rằng một hành động có thể đạt được mục tiêu nhưng vẫn gây ra những ảnh hưởng không mong muốn đối với hệ thống. Vì vậy, hiệu quả của AI Agent cần được xem xét trên nhiều khía cạnh thay vì chỉ dựa vào tỷ lệ hoàn thành nhiệm vụ.

Bajpai [8] nghiên cứu việc ứng dụng AIOps và ML vào tự động hóa quá trình xử lý sự cố mạng. Công trình trình bày một kiến trúc tổng quan gồm các giai đoạn thu thập dữ liệu, tiền xử lý, phát hiện bất thường, phân tích nguyên nhân gốc, dự đoán sự cố và tự động khắc phục. Cách tiếp cận này cho thấy hoạt động troubleshooting có thể được tổ chức thành nhiều bước xử lý liên quan đến dữ liệu và hành động vận hành. Tuy nhiên, nghiên cứu chủ yếu trình bày kiến trúc AIOps ở mức tổng quan, chưa tập trung vào cơ chế phối hợp giữa các LLM Agent chuyên trách.

Nhìn chung, NIKA cung cấp cơ sở cho việc phân chia và đánh giá các nhiệm vụ chẩn đoán sự cố, NETARENA đưa ra phương pháp đánh giá hành vi của agent trong môi trường có thể thực thi, trong khi nghiên cứu của Bajpai mô tả các giai đoạn xử lý trong một hệ thống AIOps. Những công trình này cung cấp cơ sở tham khảo cho việc thiết kế các chức năng thu thập thông tin, phân tích trạng thái, xác định nguyên nhân và hỗ trợ khắc phục sự cố trong hệ thống đề xuất.

### 1.2.4. Multi-Agent trong quản lý sự cố

Các nhiệm vụ quản lý và xử lý sự cố hệ thống thường bao gồm nhiều hoạt động có mối liên hệ với nhau, từ tiếp nhận yêu cầu, thu thập dữ liệu, phân tích trạng thái đến xác định nguyên nhân và lựa chọn phương án xử lý. Việc tổ chức những hoạt động này trong một hệ thống AI đặt ra yêu cầu về phân chia trách nhiệm, quản lý luồng thông tin và phối hợp giữa các thành phần.

Luo và cộng sự [6] đề xuất OpsAgent, một hệ thống Multi-Agent phục vụ quản lý sự cố (Incident Management) trong môi trường microservice. Hệ thống hướng đến các nhiệm vụ như phát hiện bất thường, phân loại sự cố và xác định thành phần gây ra lỗi. OpsAgent được xây dựng trên ba thành phần chính: bộ xử lý dữ liệu vận hành, cơ chế phối hợp giữa nhiều agent và cơ chế tích lũy, cải thiện năng lực xử lý qua quá trình sử dụng. Trong kiến trúc OpsAgent, dữ liệu quan sát từ hệ thống, bao gồm metrics, logs và traces, được xử lý và chuyển đổi thành các mô tả có cấu trúc để phục vụ quá trình phân tích. Các agent chuyên trách thực hiện những nhiệm vụ khác nhau dưới sự điều phối của Orchestrator. Hệ thống còn sử dụng cơ chế kiểm tra chéo (Cross-review), trong đó các agent xem xét kết quả và bằng chứng do những agent khác đưa ra nhằm phát hiện thông tin còn thiếu hoặc các nhận định cần được điều chỉnh.

Mặc dù OpsAgent không trực tiếp nghiên cứu cấu hình thiết bị mạng, nhưng nghiên cứu cung cấp cơ sở tham khảo cho việc thiết kế kiến trúc Multi-Agent với các thành phần có trách nhiệm chuyên biệt.

## 1.3. Nhận xét và khoảng trống nghiên cứu

Qua các công trình đã khảo sát, có thể nhận thấy LLM và AI Agent đang được ứng dụng trong nhiều nhiệm vụ quản lý và vận hành mạng. Các nghiên cứu tổng quan của Hong và cộng sự [1] và Zhang và cộng sự [7] cho thấy tiềm năng của LLM trong tự động hóa vận hành, đồng thời chỉ ra những thách thức về độ tin cậy, kiến thức chuyên ngành và tính an toàn.

Trong lĩnh vực cấu hình mạng, LLM-NetCFG [2] nghiên cứu việc chuyển đổi yêu cầu ngôn ngữ tự nhiên thành cấu hình thiết bị, trong khi NetConfArena [5] tập trung đánh giá khả năng thực hiện các tác vụ cấu hình của AI Agent trong môi trường có thể thực thi. Đối với xử lý sự cố, NIKA [3] đánh giá khả năng phát hiện, định vị và xác định nguyên nhân gốc; NETARENA [4] cung cấp phương pháp đánh giá AI Agent dựa trên tính đúng đắn, độ an toàn và thời gian thực thi. Bên cạnh đó, Bajpai [8] trình bày hướng tiếp cận sử dụng AIOps và Machine Learning để tự động hóa quy trình xử lý sự cố mạng.

Về kiến trúc hệ thống, OpsAgent [6] đề xuất phương pháp tổ chức các agent chuyên trách và phối hợp thực hiện nhiệm vụ quản lý sự cố trong môi trường microservice. Công trình cung cấp cơ sở tham khảo cho việc thiết kế hệ thống Multi-Agent, nhưng không trực tiếp tập trung vào cấu hình và xử lý sự cố trên thiết bị mạng.

Nhìn chung, các nghiên cứu đã cung cấp những phương pháp và công cụ cho từng nhóm nhiệm vụ. Trong phạm vi các tài liệu khảo sát, việc thiết kế và tích hợp các chức năng lập kế hoạch, tương tác thiết bị, phân tích trạng thái và hỗ trợ khắc phục sự cố trong một kiến trúc Multi-Agent thống nhất vẫn là vấn đề cần tiếp tục nghiên cứu và đánh giá.

**Bảng 1.1. Tổng hợp đóng góp và khoảng trống của các nghiên cứu liên quan**

| Tài liệu | Hướng nghiên cứu                                                 | Đóng góp đối với đề tài                                                                                                                                        | Hạn chế và khoảng trống liên quan                                                                                                                             |
| -------- | ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [1]      | Khảo sát ứng dụng LLM trong quản lý và vận hành mạng             | Cung cấp cơ sở tổng quan để xác định các nhóm nhiệm vụ mà LLM có thể hỗ trợ, gồm cấu hình, quản lý sự cố, bảo mật và điều phối hoạt động mạng.                 | Là nghiên cứu khảo sát, chưa đề xuất một quy trình Multi-Agent hoàn chỉnh có khả năng kiểm soát việc thực thi trên thiết bị mạng.                             |
| [2]      | Quản lý cấu hình mạng Zero-Touch bằng LLM                        | Làm cơ sở cho việc chuyển đổi yêu cầu ngôn ngữ tự nhiên thành cấu hình, đồng thời cho thấy sự cần thiết của bước xác minh trước khi triển khai.                | Chủ yếu tập trung vào sinh và kiểm tra cấu hình; chưa đánh giá toàn diện quá trình troubleshooting, Human-in-the-loop và truy vết thực thi.                   |
| [3]      | Benchmark AI Agent trong Network Troubleshooting                 | Cung cấp cách phân tách nhiệm vụ thành phát hiện, định vị và xác định nguyên nhân gốc; là cơ sở tham khảo cho mô hình Ground Truth và các chỉ số đánh giá RCA. | Tập trung vào đánh giá Agent; không cung cấp đầy đủ một hệ thống quản trị tích hợp gồm quản lý người dùng, thiết bị, phê duyệt cấu hình và nhật ký kiểm toán. |
| [4]      | Benchmark động cho AI Agent trong Network Automation             | Gợi ý cách đánh giá hành vi Agent dựa trên tính đúng đắn, độ an toàn và thời gian thực thi trong môi trường có thể tương tác.                                  | Mục tiêu chính là xây dựng benchmark tổng quát; chưa tập trung vào quy trình điều phối Multi-Agent và Human-in-the-loop trên GNS3.                            |
| [5]      | Benchmark cấu hình mạng theo vòng kín                            | Khẳng định kết quả cấu hình cần được đánh giá theo trạng thái và hành vi thực tế của mạng thay vì chỉ so sánh chuỗi lệnh.                                      | Chưa bao quát đầy đủ bài toán quản trị thiết bị, phân quyền, audit và chẩn đoán nguyên nhân sự cố trong một ứng dụng quản trị thống nhất.                     |
| [6]      | Multi-Agent cho quản lý sự cố trong hệ thống microservice        | Cung cấp cơ sở thiết kế các Agent chuyên trách, Orchestrator và cơ chế kiểm tra chéo dựa trên bằng chứng.                                                      | Đối tượng nghiên cứu là microservice với metrics, logs và traces; không trực tiếp xử lý cấu hình hoặc giao thức trên thiết bị mạng.                           |
| [7]      | Khảo sát AIOps trong kỷ nguyên LLM                               | Hệ thống hóa các nguồn dữ liệu, nhiệm vụ quản lý sự cố và phương pháp ứng dụng LLM trong vận hành hệ thống.                                                    | Phạm vi nghiên cứu rộng và chủ yếu mang tính khảo sát; chưa cụ thể hóa quy trình tương tác, phê duyệt và kiểm chứng trên thiết bị mạng.                       |
| [8]      | Ứng dụng AIOps và Machine Learning trong Network Troubleshooting | Cung cấp mô hình tham khảo cho chuỗi thu thập dữ liệu, phát hiện bất thường, RCA, dự đoán và khắc phục sự cố.                                                  | Kiến trúc được trình bày ở mức tổng quan; chưa tích hợp LLM, các Agent chuyên trách và cơ chế điều phối thực thi có kiểm soát.                                |

Bảng 1.1 cho thấy các công trình đã cung cấp cơ sở quan trọng cho từng khía cạnh riêng lẻ của bài toán, bao gồm ứng dụng LLM, sinh cấu hình, Network Troubleshooting, kiến trúc Multi-Agent và phương pháp benchmark. Tuy nhiên, trong phạm vi các tài liệu khảo sát, chưa có công trình nào đồng thời tích hợp việc tiếp nhận yêu cầu bằng ngôn ngữ tự nhiên, lập kế hoạch, tương tác trực tiếp với thiết bị, thu thập bằng chứng, phân tích nguyên nhân gốc, phê duyệt thay đổi cấu hình và đánh giá kết quả trong một quy trình Multi-Agent thống nhất trên môi trường GNS3. Khoảng trống này là cơ sở để đề tài xác lập hướng tiếp cận được trình bày tại mục 1.4.

## 1.4. Hướng tiếp cận của đề tài

Trên cơ sở phân tích các công trình liên quan và xác định những vấn đề cần tiếp tục nghiên cứu, đề tài lựa chọn hướng tiếp cận xây dựng hệ thống Multi-Agent hỗ trợ cấu hình và xử lý sự cố mạng thông qua giao tiếp bằng ngôn ngữ tự nhiên. Hệ thống được thiết kế theo kiến trúc phân chia nhiệm vụ, trong đó mô hình ngôn ngữ lớn đảm nhiệm vai trò phân tích yêu cầu và hỗ trợ ra quyết định, còn các thành phần điều phối và xử lý nghiệp vụ chịu trách nhiệm kiểm soát quá trình thực hiện. Cách tiếp cận này nhằm khai thác khả năng xử lý ngôn ngữ của LLM, đồng thời hạn chế việc để mô hình trực tiếp quyết định và thực thi những thao tác có thể làm thay đổi trạng thái thiết bị mạng.

Về tổ chức kiến trúc, hệ thống sử dụng các Agent chuyên trách, bao gồm Planner Agent, Configuration Agent, Network Agent và Analyst Agent. Planner Agent phân tích yêu cầu và xây dựng kế hoạch ở mức nghiệp vụ; Configuration Agent chuyển yêu cầu thay đổi đã lập kế hoạch thành câu lệnh CLI phù hợp; Network Agent tương tác với thiết bị thông qua công cụ quản trị mạng; Analyst Agent phân tích thông tin và đánh giá kết quả xử lý. Thành phần điều phối trung tâm kiểm soát thứ tự thực hiện, trạng thái nhiệm vụ và các điều kiện nghiệp vụ trong từng giai đoạn.

Đối với quá trình thực thi, đề tài tổ chức các nhiệm vụ thành những thao tác có cấu trúc, xác định rõ thiết bị liên quan, thứ tự thực hiện, quan hệ phụ thuộc và phạm vi truy cập. Thông tin thiết bị được quản lý tập trung nhằm giới hạn đối tượng mà hệ thống có thể tương tác, đồng thời các thao tác đọc thông tin và thay đổi cấu hình được phân biệt để áp dụng cơ chế kiểm soát phù hợp. Đặc biệt, những thao tác làm thay đổi cấu hình thiết bị phải trải qua bước phê duyệt của người dùng trước khi thực thi. Hệ thống cũng thực hiện kiểm tra tính nhất quán của nội dung đã được phê duyệt nhằm hạn chế nguy cơ thực thi những thay đổi ngoài phạm vi cho phép.

Bên cạnh đó, đề tài chú trọng khả năng theo dõi và truy vết quá trình xử lý thông qua việc quản lý trạng thái nhiệm vụ, ghi nhận các thao tác thực thi và lưu trữ lịch sử hoạt động. Mỗi yêu cầu của người dùng được liên kết với một nhiệm vụ cụ thể, cho phép theo dõi tiến trình từ giai đoạn tiếp nhận, lập kế hoạch đến thực hiện và đánh giá kết quả. Những thông tin này hỗ trợ việc kiểm tra, phân tích các tình huống phát sinh và xác định nguyên nhân khi nhiệm vụ không đạt kết quả mong đợi. Đồng thời, hệ thống áp dụng các cơ chế bảo vệ thông tin xác thực thiết bị nhằm hạn chế việc truy cập và sử dụng thông tin nhạy cảm không cần thiết.

Về thực nghiệm, đề tài triển khai hệ thống trong môi trường mô phỏng GNS3 với các thiết bị mạng ảo hóa và những kịch bản cấu hình, xử lý sự cố được xác định trước. Các kịch bản thực nghiệm được xây dựng dựa trên trạng thái ban đầu, yêu cầu nhiệm vụ, nguyên nhân sự cố và kết quả mong đợi, tạo điều kiện đánh giá hoạt động của hệ thống theo những tiêu chí có thể kiểm chứng. Quá trình đánh giá tập trung vào khả năng hoàn thành nhiệm vụ, độ chính xác trong xác định nguyên nhân sự cố, hiệu quả khắc phục, mức độ tuân thủ các điều kiện an toàn và thời gian thực hiện. Kết quả được ghi nhận và tổng hợp nhằm phục vụ việc phân tích hiệu quả của hệ thống trong những điều kiện thử nghiệm khác nhau.

Phạm vi nghiên cứu của đề tài tập trung vào việc thiết kế, xây dựng và đánh giá hệ thống Multi-Agent trong môi trường mạng mô phỏng. Các nội dung như kiểm chứng trên hạ tầng mạng thực tế, giám sát telemetry liên tục, tự động khôi phục cấu hình và bảo đảm chính sách mạng trong toàn bộ vòng đời vận hành chưa được xem xét trong phạm vi triển khai. Thông qua hướng tiếp cận này, đề tài hướng đến việc đánh giá tính khả thi của việc kết hợp LLM, kiến trúc Multi-Agent và các cơ chế kiểm soát thực thi trong một hệ thống hỗ trợ quản trị mạng có khả năng theo dõi, kiểm chứng và đánh giá kết quả.

---

# CHƯƠNG 2. CƠ SỞ LÝ THUYẾT VÀ CÔNG NGHỆ

## 2.1. Tổng quan về mô hình ngôn ngữ lớn (Large Language Models)

### 2.1.1. Khái niệm mô hình ngôn ngữ lớn

Mô hình ngôn ngữ lớn (Large Language Model – LLM) là một lớp mô hình học sâu được huấn luyện trên tập dữ liệu văn bản quy mô lớn nhằm học các quy luật và mối quan hệ trong ngôn ngữ tự nhiên. Theo Zhao và cộng sự [9], LLM có khả năng thực hiện nhiều nhiệm vụ xử lý ngôn ngữ tự nhiên như sinh văn bản, trả lời câu hỏi, dịch máy, tóm tắt và phân tích nội dung. Sự phát triển của các mô hình này gắn liền với việc mở rộng quy mô tham số, dữ liệu huấn luyện và tài nguyên tính toán, kết hợp với những cải tiến về kiến trúc và phương pháp huấn luyện.

Về nguyên lý hoạt động, nhiều mô hình ngôn ngữ sinh văn bản sử dụng phương pháp dự đoán xác suất xuất hiện của token tiếp theo dựa trên các token đã có trong ngữ cảnh. Thông qua quá trình huấn luyện, mô hình học được những đặc trưng ngôn ngữ và có thể tạo ra phản hồi phù hợp với dữ liệu đầu vào. Tuy nhiên, khả năng tạo ra văn bản mạch lạc không đồng nghĩa với việc mọi thông tin được sinh ra đều chính xác.

### 2.1.2. Kiến trúc Transformer

Theo Vaswani và cộng sự [10], Transformer là kiến trúc mạng nơ-ron được xây dựng dựa trên cơ chế Attention nhằm mô hình hóa mối quan hệ giữa các thành phần trong chuỗi dữ liệu. Khác với những kiến trúc mạng hồi quy truyền thống, Transformer không phụ thuộc vào cơ chế hồi quy để xử lý toàn bộ chuỗi, qua đó tạo điều kiện thuận lợi cho việc xử lý song song trong quá trình huấn luyện và nâng cao khả năng học các quan hệ phụ thuộc giữa những vị trí trong chuỗi.

Một thành phần quan trọng của Transformer là Self-Attention, cho phép mô hình tổng hợp thông tin từ những vị trí khác nhau trong chuỗi. Cơ chế Scaled Dot-Product Attention được biểu diễn như sau:

$$
\operatorname{Attention}(Q,K,V)=\operatorname{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V
$$

Trong đó, $Q$, $K$ và $V$ lần lượt là các ma trận truy vấn, khóa và giá trị; $d_k$ là số chiều của vector khóa. Phép toán softmax chuẩn hóa các điểm Attention thành trọng số, từ đó xác định mức độ đóng góp của các vector giá trị vào biểu diễn đầu ra.

### 2.1.3. Hạn chế của mô hình ngôn ngữ lớn

Mặc dù đạt được nhiều tiến bộ trong xử lý và sinh ngôn ngữ tự nhiên, các mô hình ngôn ngữ lớn vẫn tồn tại những hạn chế về độ chính xác, tính nhất quán và khả năng kiểm chứng thông tin. Những vấn đề này đặc biệt đáng lưu ý khi LLM được tích hợp vào các hệ thống yêu cầu độ tin cậy cao hoặc có khả năng tác động đến môi trường bên ngoài.

Một trong những hạn chế đáng chú ý là hiện tượng hallucination, khi mô hình tạo ra nội dung có vẻ hợp lý nhưng không được hỗ trợ bởi nguồn thông tin hoặc không phản ánh đúng thực tế. Theo Ji và cộng sự (2023) [11], hiện tượng này có thể biểu hiện qua việc tạo ra thông tin không nhất quán với dữ liệu nguồn hoặc sai lệch so với tri thức thực tế, làm giảm độ tin cậy của kết quả trong các nhiệm vụ đòi hỏi tính chính xác.

Bên cạnh đó, chất lượng phản hồi của LLM phụ thuộc vào cách diễn đạt yêu cầu, ngữ cảnh và dữ liệu đầu vào. Những thay đổi trong cách cung cấp thông tin có thể dẫn đến kết quả khác nhau, ngay cả với các yêu cầu tương tự. Ngoài ra, mô hình có thể đưa ra lập luận thiếu chính xác hoặc không tuân thủ đầy đủ các ràng buộc kỹ thuật, đặc biệt trong những nhiệm vụ yêu cầu xử lý nhiều bước.

Trong lĩnh vực quản trị và tự động hóa mạng, các hạn chế này có thể dẫn đến việc phân tích sai trạng thái thiết bị, xác định không chính xác nguyên nhân sự cố hoặc đề xuất cấu hình không phù hợp. Nếu được thực thi mà không qua kiểm tra, những kết quả này có nguy cơ gây ra thay đổi ngoài mong muốn và ảnh hưởng đến hoạt động của hệ thống mạng.

Do đó, việc ứng dụng LLM trong quản trị mạng cần kết hợp với các cơ chế kiểm tra tính hợp lệ, xác minh kết quả và kiểm soát thực thi. Những biện pháp như đối chiếu trạng thái thiết bị, kiểm tra cấu hình và yêu cầu phê duyệt trước khi thực hiện thay đổi góp phần hạn chế rủi ro. Đây là cơ sở cho việc phát triển các hệ thống AI Agent vừa khai thác khả năng của LLM, vừa duy trì sự kiểm soát đối với những thao tác trên hạ tầng mạng.

## 2.2. AI Agent và Multi-Agent System

### 2.2.1. Khái niệm AI Agent

AI Agent là một thực thể có khả năng nhận thông tin từ môi trường, đưa ra quyết định và thực hiện hành động nhằm đạt được mục tiêu xác định. Theo Wooldridge và Jennings (1995) [12], các đặc tính quan trọng của agent bao gồm tính tự chủ (autonomy), khả năng phản ứng với môi trường (reactivity), tính chủ động (pro-activeness) và khả năng tương tác xã hội (social ability).

Trong các hệ thống trí tuệ nhân tạo hiện đại, LLM có thể được sử dụng làm thành phần hỗ trợ ra quyết định cho agent. Theo Xi và cộng sự (2025) [13], các LLM-based Agent có thể kết hợp khả năng xử lý ngôn ngữ tự nhiên với các cơ chế lập kế hoạch, ghi nhớ, sử dụng công cụ và tương tác với môi trường, qua đó hỗ trợ thực hiện những nhiệm vụ phức tạp đòi hỏi nhiều bước xử lý liên tiếp.

Khác với chatbot chỉ tạo phản hồi văn bản, AI Agent có thể tham gia vào quy trình thực hiện nhiệm vụ thông qua việc lựa chọn hành động và tiếp nhận kết quả từ những công cụ bên ngoài. Tuy nhiên, không phải mọi agent đều bắt buộc sử dụng LLM; một số agent có thể hoạt động dựa trên quy tắc hoặc các cơ chế xử lý xác định trước, tùy thuộc vào mục tiêu và yêu cầu hệ thống.

### 2.2.2. Khái niệm Multi-Agent System

Multi-Agent System (MAS) là hệ thống gồm nhiều agent hoạt động trong một môi trường và có khả năng tương tác để thực hiện những nhiệm vụ hoặc đạt được các mục tiêu xác định. Các agent có thể phối hợp, trao đổi thông tin và phân chia trách nhiệm trong quá trình thực hiện nhiệm vụ chung.

Trong những hệ thống ứng dụng LLM, kiến trúc Multi-Agent cho phép phân chia nhiệm vụ thành các chức năng chuyên biệt. Theo Wu và cộng sự (2024) [14], framework AutoGen được đề xuất nhằm hỗ trợ xây dựng các ứng dụng LLM thông qua sự tương tác giữa nhiều agent, trong đó các agent có thể được cấu hình với vai trò, công cụ và phương thức phối hợp khác nhau.

Cách tiếp cận Multi-Agent tạo điều kiện tổ chức các nhiệm vụ phức tạp thành nhiều bước xử lý có trách nhiệm rõ ràng, đồng thời hỗ trợ phân công và theo dõi tiến trình thực hiện của từng agent trong hệ thống. Tuy nhiên, hiệu quả của hệ thống phụ thuộc vào cách thiết kế cơ chế phối hợp và kiểm soát thông tin giữa các thành phần.

### 2.2.3. Cơ chế phối hợp và những thách thức của Multi-Agent System

Quá trình phối hợp giữa các agent có thể được tổ chức theo cơ chế tập trung, phân tán hoặc phân cấp. Trong mô hình tập trung, một thành phần điều phối chịu trách nhiệm quản lý luồng thực thi và phân công nhiệm vụ. Trong mô hình phân tán, các agent có thể trao đổi thông tin và phối hợp trực tiếp với nhau. Đối với mô hình phân cấp, các agent được tổ chức theo các cấp quản lý và thực thi khác nhau.

Theo Wu và cộng sự (2024) [14], sự phối hợp giữa nhiều agent có thể được sử dụng để xây dựng những quy trình xử lý linh hoạt, trong đó các agent trao đổi thông tin, gọi công cụ và kết hợp kết quả để thực hiện nhiệm vụ.

Tuy nhiên, việc sử dụng nhiều agent cũng làm gia tăng độ phức tạp trong điều phối, quản lý trạng thái, giao tiếp và kiểm soát quá trình thực thi. Vì vậy, việc xây dựng hệ thống Multi-Agent cần xác định rõ vai trò, phạm vi trách nhiệm và phương thức trao đổi dữ liệu giữa các agent, đồng thời bảo đảm tính nhất quán và khả năng kiểm soát trong toàn bộ quy trình xử lý.

## 2.3. Network Automation

### 2.3.1. Khái niệm Network Automation

Network Automation (tự động hóa mạng) là việc ứng dụng phần mềm và các cơ chế điều khiển tự động nhằm thực hiện những tác vụ liên quan đến cấu hình, giám sát và quản lý hệ thống mạng. Phương pháp này giúp giảm thao tác thủ công, nâng cao hiệu quả và bảo đảm tính nhất quán trong quản lý thiết bị mạng.

Các nghiên cứu về tự động hóa mạng hướng đến việc giảm sự phụ thuộc vào thao tác thủ công và tăng khả năng vận hành nhất quán trong những môi trường mạng có cấu trúc phức tạp. Đặc biệt, các phương pháp Zero-Touch Management hướng đến khả năng tự động hóa các hoạt động quản lý và vận hành với sự giám sát phù hợp của con người [15].

Trong thực tế, Network Automation có thể bao gồm những thành phần như hệ thống quản lý thiết bị, mô hình dữ liệu, cơ chế kết nối, bộ thực thi tác vụ và thành phần điều phối. Những thành phần này hỗ trợ tổ chức các thao tác trên nhiều thiết bị thành các quy trình có thể kiểm tra và thực hiện lại.

### 2.3.2. Nguyên lý hoạt động và yêu cầu của Network Automation

Tự động hóa mạng có thể được thực hiện ở mức tác vụ hoặc mức quy trình, tùy thuộc vào phạm vi và yêu cầu vận hành của hệ thống. Tự động hóa tác vụ tập trung vào một thao tác cụ thể như thu thập thông tin thiết bị, kiểm tra trạng thái hoặc thay đổi cấu hình. Trong khi đó, tự động hóa quy trình kết hợp nhiều tác vụ theo trình tự xác định, có thể bao gồm điều kiện thực thi, quan hệ phụ thuộc và xử lý ngoại lệ nhằm bảo đảm tính nhất quán trong quá trình vận hành mạng.

Theo nghiên cứu tổng quan về Zero-Touch Management [15], các hệ thống tự động hóa có thể sử dụng dữ liệu giám sát, thông tin trạng thái và các cơ chế ra quyết định nhằm hỗ trợ điều chỉnh hoạt động mạng. Trong những hệ thống có cơ chế phản hồi, kết quả quan sát được sử dụng để đánh giá và lựa chọn những hành động tiếp theo, qua đó hình thành quy trình điều khiển có khả năng thích ứng với sự thay đổi của môi trường mạng.

Để bảo đảm độ tin cậy, một hệ thống Network Automation cần chú trọng khả năng kiểm soát thao tác, xử lý lỗi, ghi nhận kết quả và xác minh trạng thái sau thực thi. Ngoài ra, tính idempotent là một đặc tính quan trọng đối với các thao tác có thể thực hiện lặp lại mà không gây ra những thay đổi ngoài mong muốn sau lần thực hiện đầu tiên. Đặc tính này góp phần duy trì tính nhất quán của cấu hình và hạn chế rủi ro khi thực hiện lại các tác vụ tự động hóa.

## 2.4. Network Troubleshooting và Root Cause Analysis

### 2.4.1. Khái niệm Network Troubleshooting

Network Troubleshooting là quá trình phát hiện, phân tích và xử lý những sự cố ảnh hưởng đến hoạt động của hệ thống mạng. Quá trình này thường bao gồm nhận diện triệu chứng, thu thập thông tin, xây dựng giả thuyết, xác định vị trí lỗi, kiểm tra nguyên nhân và xác minh trạng thái sau xử lý.

Trong nghiên cứu về ứng dụng LLM vào quản lý và vận hành mạng, Hong và cộng sự (2025) [1] khảo sát các hướng ứng dụng mô hình ngôn ngữ lớn nhằm hỗ trợ những nhiệm vụ vận hành, bao gồm phân tích và xử lý sự cố mạng.

Các nguồn thông tin phục vụ quá trình chẩn đoán có thể bao gồm trạng thái giao diện mạng, bảng định tuyến, cấu hình thiết bị, nhật ký hệ thống và kết quả kiểm tra kết nối. Việc tổng hợp những dữ liệu này giúp xác định các biểu hiện bất thường và hỗ trợ khoanh vùng sự cố.

### 2.4.2. Root Cause Analysis

Root Cause Analysis (RCA) là quá trình phân tích nhằm xác định nguyên nhân gốc gây ra sự cố thay vì chỉ xử lý các triệu chứng quan sát được. Trong hệ thống mạng, một nguyên nhân có thể tạo ra nhiều biểu hiện khác nhau tại các thiết bị và dịch vụ có quan hệ phụ thuộc. Vì vậy, quá trình RCA cần phân biệt giữa triệu chứng, vị trí lỗi và nguyên nhân dẫn đến sự cố.

Theo Wang và cộng sự (2025) [3], NIKA đề xuất môi trường đánh giá AI Agent cho bài toán Network Troubleshooting, trong đó phân chia hoạt động chẩn đoán thành ba nhiệm vụ gồm phát hiện sự cố (Detection), xác định vị trí lỗi (Localization) và xác định nguyên nhân gốc (Root Cause Identification).

Đối với hệ thống sử dụng AI Agent, kết quả phân tích nguyên nhân cần được liên kết với bằng chứng thu thập từ môi trường. Việc đưa ra kết luận khi chưa có đủ thông tin có thể dẫn đến đề xuất biện pháp khắc phục không phù hợp. Do đó, cần đối chiếu kết quả phân tích với trạng thái thiết bị trước khi kết luận.

## 2.5. Các phương pháp kiểm tra và kiểm soát thực thi cấu hình

### 2.5.1. Kiểm tra cấu hình trước và sau thực thi

Trong các hệ thống tự động hóa mạng, việc thay đổi cấu hình cần được kiểm soát nhằm hạn chế nguy cơ gián đoạn dịch vụ hoặc làm thay đổi trạng thái mạng ngoài mong muốn. Quá trình kiểm soát có thể bao gồm xác thực yêu cầu, phân quyền thực thi, kiểm tra tính hợp lệ của kế hoạch, xác định phạm vi tác động và đánh giá trạng thái mạng trước khi thay đổi cấu hình, nhằm bảo đảm các thao tác được thực hiện đúng mục tiêu và yêu cầu kỹ thuật.

Trong nghiên cứu của Lira và cộng sự (2024) [2], việc ứng dụng LLM để hỗ trợ quản lý cấu hình mạng được kết hợp với quá trình xác minh nhằm kiểm tra tính phù hợp của cấu hình được tạo ra, qua đó góp phần hạn chế những sai lệch giữa yêu cầu ban đầu và kết quả cấu hình.

Bên cạnh đó, NetConfArena của Liu và cộng sự (2026) [5] nhấn mạnh việc đánh giá kết quả cấu hình thông qua môi trường mạng có thể thực thi. Cách tiếp cận này cho phép kiểm tra kết quả dựa trên trạng thái mạng đạt được, thay vì chỉ đánh giá tính hợp lệ về cú pháp của các câu lệnh, đồng thời hỗ trợ phát hiện những vấn đề có thể phát sinh trong quá trình vận hành hệ thống.

Sau khi thực thi, hệ thống cần thu thập trạng thái thiết bị và đối chiếu với kết quả mong muốn. Trong trường hợp không đáp ứng điều kiện kiểm chứng, hệ thống cần ghi nhận lỗi và thực hiện quy trình xử lý phù hợp, đồng thời lưu lại thông tin thực thi để phục vụ việc phân tích và khắc phục sự cố.

### 2.5.2. Human-in-the-loop và cơ chế phê duyệt

Human-in-the-loop là cơ chế tích hợp sự tham gia của con người vào một hoặc nhiều bước ra quyết định trong quy trình xử lý tự động.

Trong lĩnh vực quản trị mạng, cơ chế này phù hợp với các thao tác có khả năng thay đổi trạng thái thiết bị hoặc ảnh hưởng đến hoạt động của dịch vụ. Thay vì cho phép hệ thống thực hiện mọi hành động được đề xuất, người quản trị có thể xem xét và phê duyệt những thay đổi trước khi thực thi.

Quy trình phê duyệt cần gắn với nội dung thay đổi cụ thể, phạm vi tác động và danh tính người phê duyệt. Bên cạnh đó, việc ghi nhận nhật ký hoạt động giúp hỗ trợ truy vết các quyết định và những thao tác đã được thực hiện.

Cơ chế Human-in-the-loop góp phần hạn chế quyền tự quyết trực tiếp của AI Agent đối với các hành động có rủi ro, nhưng bản thân việc phê duyệt không bảo đảm cấu hình được chấp thuận luôn chính xác hoặc an toàn.

## 2.6. Mô hình Pregel và nguyên lý điều phối đồ thị

### 2.6.1. Mô hình Pregel và Bulk Synchronous Parallel

Theo Malewicz và cộng sự (2010) [16], Pregel là một hệ thống được đề xuất nhằm xử lý đồ thị quy mô lớn trên môi trường tính toán song song. Pregel sử dụng mô hình lập trình hướng đỉnh (vertex-centric), trong đó các đỉnh thực hiện tính toán cục bộ và trao đổi thông tin thông qua cơ chế truyền thông điệp.

Mô hình Pregel được xây dựng dựa trên nguyên lý Bulk Synchronous Parallel (BSP). Theo đó, quá trình tính toán được chia thành các vòng xử lý gọi là superstep, với những điểm đồng bộ giữa các vòng liên tiếp.

Trong mỗi superstep, các đỉnh đang hoạt động có thể nhận những thông điệp từ vòng trước, thực hiện tính toán, cập nhật trạng thái cục bộ và gửi thông điệp cho các đỉnh khác. Những thông điệp được gửi sẽ được xử lý ở superstep tiếp theo.

Quá trình tính toán kết thúc khi các đỉnh đều ngừng hoạt động và không còn thông điệp đang chờ xử lý.

### 2.6.2. Nguyên lý thực thi theo Superstep

Dựa trên nguyên lý Pregel, quá trình thực thi có thể được mô tả thông qua các vòng xử lý có đồng bộ trạng thái. Mỗi vòng sử dụng dữ liệu đã có từ vòng trước để xác định hoạt động tính toán và tạo ra các kết quả phục vụ vòng tiếp theo.

Ở mức khái quát, một chu trình thực thi dựa trên superstep có thể được chia thành ba giai đoạn:

1. Xác định các thành phần cần thực thi dựa trên trạng thái hiện tại và thông tin được cập nhật từ vòng trước.
2. Thực hiện tính toán tại những thành phần đã được lựa chọn, đồng thời tạo ra các cập nhật hoặc thông điệp.
3. Đồng bộ các cập nhật để hình thành trạng thái sử dụng cho superstep kế tiếp.

Cách tổ chức này cho phép biểu diễn các quá trình xử lý có quan hệ phụ thuộc, trong đó kết quả của một vòng được sử dụng làm dữ liệu đầu vào cho những vòng tiếp theo.

Nguyên lý superstep cũng cung cấp cơ sở tham khảo cho các hệ thống điều phối workflow dạng đồ thị. Tuy nhiên, việc vận dụng Pregel vào điều phối AI Agent không đồng nghĩa với việc triển khai một hệ thống xử lý đồ thị phân tán tương đương Pregel gốc.

## 2.7. Cơ sở đánh giá hệ thống AI Agent trong quản trị mạng

### 2.7.1. Phương pháp đánh giá AI Agent trong môi trường mạng

Việc đánh giá hệ thống AI Agent trong quản trị mạng cần xem xét không chỉ khả năng tạo phản hồi phù hợp mà còn tính chính xác của các hành động và trạng thái mạng sau thực thi. Khác với các nhiệm vụ xử lý ngôn ngữ tự nhiên thông thường, kết quả của một tác vụ cấu hình hoặc xử lý sự cố mạng cần được kiểm chứng thông qua trạng thái thực tế của thiết bị và các điều kiện kỹ thuật xác định trước.

Theo Wang và cộng sự (2025) [3], NIKA cung cấp môi trường đánh giá AI Agent trong bài toán Network Troubleshooting, tập trung vào ba nhiệm vụ có mức độ phức tạp tăng dần: phát hiện sự cố (Detection), xác định vị trí lỗi (Localization) và phân tích nguyên nhân gốc (Root Cause Analysis). Phương pháp này cho phép đánh giá riêng từng khả năng chẩn đoán, thay vì chỉ dựa trên kết luận tổng thể của agent.

Bên cạnh đó, Zhou và cộng sự (2026) [4] đề xuất NETARENA, một framework đánh giá AI Agent trong các nhiệm vụ tự động hóa mạng thông qua môi trường có thể thực thi. Nghiên cứu xem xét đồng thời tính đúng đắn (Correctness), tính an toàn (Safety) và thời gian thực hiện (Latency). Tương tự, Liu và cộng sự (2026) [5] đề xuất NetConfArena, trong đó kết quả cấu hình được kiểm chứng bằng các phép kiểm tra thực thi trên môi trường mạng giả lập, thay vì chỉ so sánh những câu lệnh do mô hình tạo ra với đáp án tham chiếu.

Từ các nghiên cứu trên, việc đánh giá hệ thống Multi-Agent có thể được tổ chức dựa trên những kịch bản thực nghiệm xác định trước, bao gồm trạng thái ban đầu của mạng, yêu cầu nhiệm vụ, kết quả mong đợi và các điều kiện kiểm chứng. Kết quả thực thi được đối chiếu với dữ liệu chuẩn (Ground Truth) hoặc trạng thái mạng mục tiêu để xác định mức độ hoàn thành nhiệm vụ và những hạn chế của hệ thống.

### 2.7.2. Các tiêu chí đánh giá

Các tiêu chí đánh giá được lựa chọn nhằm phản ánh khả năng hoàn thành nhiệm vụ, chất lượng chẩn đoán, hiệu quả khắc phục sự cố, mức độ an toàn và chi phí thực thi của hệ thống Multi-Agent. Việc đánh giá được thực hiện dựa trên các kịch bản thực nghiệm có điều kiện kiểm chứng và kết quả mong đợi được xác định trước.

**Tỷ lệ hoàn thành nhiệm vụ (Task Success Rate – TSR).** Chỉ số này phản ánh tỷ lệ lượt thực nghiệm mà hệ thống hoàn thành nhiệm vụ và đáp ứng các điều kiện kiểm chứng đã xác định:

$$
TSR = \frac{N_{\mathrm{success}}}{N_{\mathrm{total}}} \times 100\%
$$

Trong đó, $N_{\mathrm{success}}$ là số lượt thực nghiệm hoàn thành nhiệm vụ thành công và $N_{\mathrm{total}}$ là tổng số lượt thực nghiệm hợp lệ được đưa vào đánh giá.

**Độ chính xác trong chẩn đoán sự cố (Diagnostic Accuracy).** Dựa trên cách phân chia nhiệm vụ trong nghiên cứu NIKA [3], khả năng chẩn đoán về mặt lý thuyết được xem xét theo ba cấp độphát hiện sự cố (Detection), xác định vị trí lỗi (Localization) và xác định nguyên nhân gốc (Root Cause Identification):

- **Detection Accuracy:** phản ánh tỷ lệ trường hợp hệ thống xác định chính xác trạng thái có hoặc không có sự cố.
- **Localization Accuracy:** phản ánh tỷ lệ trường hợp hệ thống xác định đúng thiết bị hoặc thành phần gây lỗi theo tiêu chí định vị đã xác định.
- **Root Cause Accuracy:** phản ánh tỷ lệ trường hợp hệ thống xác định đúng nguyên nhân gốc của sự cố so với dữ liệu chuẩn (Ground Truth).

Đối với từng tiêu chí, độ chính xác được xác định bằng tỷ lệ số trường hợp dự đoán đúng trên tổng số trường hợp hợp lệ thuộc phạm vi đánh giá tương ứng:

$$
Accuracy = \frac{N_{\mathrm{correct}}}{N_{\mathrm{evaluated}}} \times 100\%
$$

Trong đó, $N_{\mathrm{correct}}$ là số trường hợp được xác định chính xác và $N_{\mathrm{evaluated}}$ là tổng số trường hợp được đánh giá. Kết quả được xem là chính xác khi đáp ứng quy tắc đối chiếu với Ground Truth đã được xác định trước. Trong triển khai hiện tại, kết quả có cấu trúc được chuẩn hóa thành tập cặp `(resource_id, fault_type)` và được chấm bằng Precision, Recall và F1 cho định vị, loại lỗi và RCA tổng hợp. Vì các Benchmark Scenario hiện đều chủ động tiêm lỗi, Detection được ghi nhận dưới dạng `Detection Score` khi Analyst xác định `is_anomaly=true`; giá trị này chưa phải Detection Accuracy trên một tập dữ liệu có đồng thời trường hợp mạng lỗi và mạng khỏe.

**Tỷ lệ khắc phục sự cố thành công (Remediation Success Rate – RSR).** Chỉ số này phản ánh tỷ lệ trường hợp hệ thống thực hiện biện pháp khắc phục và đạt được trạng thái mạng mục tiêu sau khi kiểm chứng. Chỉ số được tính trên các trường hợp hợp lệ thuộc phạm vi đánh giá khắc phục sự cố:

$$
RSR = \frac{N_{\mathrm{remediated}}}{N_{\mathrm{remediation}}} \times 100\%
$$

Trong đó, $N_{\mathrm{remediated}}$ là số trường hợp khắc phục sự cố thành công và $N_{\mathrm{remediation}}$ là tổng số trường hợp được đưa vào đánh giá khắc phục. Việc xác định thành công phải dựa trên trạng thái thực tế của thiết bị và các điều kiện kiểm chứng đã quy định. Đây là tiêu chí được đề xuất về mặt lý thuyết; phiên bản evaluator hiện tại chưa có bộ chấm độc lập cho kết quả khắc phục của Agent nên metric `REMEDIATION` được lưu ở trạng thái `NOT_APPLICABLE`.

**Tính an toàn (Safety).** Tiêu chí này phản ánh khả năng hệ thống tuân thủ các chính sách và ràng buộc trong quá trình thực thi, bao gồm quyền truy cập, phạm vi thiết bị được phép thao tác, yêu cầu phê duyệt và điều kiện an toàn của cấu hình. Một phương pháp đánh giá là xác định tỷ lệ lượt thực nghiệm không phát sinh hành động vi phạm chính sách:

$$
SafetyRate = \frac{N_{\mathrm{safe}}}{N_{\mathrm{safety}}} \times 100\%
$$

Trong đó, $N_{\mathrm{safe}}$ là số lượt thực nghiệm không xảy ra hành động vi phạm chính sách và $N_{\mathrm{safety}}$ là tổng số lượt thực nghiệm hợp lệ được đánh giá về an toàn. Chỉ số này chỉ được sử dụng khi hệ thống có bộ quy tắc và cơ chế ghi nhận hành vi vi phạm độc lập. Phiên bản evaluator hiện tại chưa triển khai Safety Scorer đầy đủ nên metric `SAFETY` được lưu ở trạng thái `NOT_APPLICABLE`; trạng thái này không được diễn giải thành hệ thống an toàn tuyệt đối hoặc điểm an toàn bằng 0%.

**Thời gian thực thi (Latency).** Chỉ số này phản ánh khoảng thời gian hệ thống cần để xử lý một nhiệm vụ, tính từ thời điểm bắt đầu đến khi hoàn thành hoặc đạt trạng thái kết thúc được quy định:

$$
Latency = t_{\mathrm{end}} - t_{\mathrm{start}}
$$

Trong đó, $t_{\mathrm{start}}$ là thời điểm bắt đầu xử lý và $t_{\mathrm{end}}$ là thời điểm kết thúc. Trong triển khai hiện tại, `Active workflow latency` được tính từ thời điểm tạo Task đến khi tạo `FINAL_RESPONSE`, sau khi loại trừ thời gian chờ phê duyệt của con người. Chỉ số bao gồm thời gian của Planner, Configuration, Network, Analyst và phần điều phối, không bao gồm bước chuẩn bị GNS3 và không được xem là thời gian suy luận LLM thuần túy.

**Số lượt tương tác (Interaction Turns).** Trong triển khai hiện tại, chỉ số này được định nghĩa là số lượt Agent gọi công cụ mạng có bản ghi `TaskExecution` và `tool_name` hợp lệ. Chỉ số không đếm số Message, số lượt gọi LLM, số node LangGraph, thao tác tiêm lỗi hoặc cleanup của Benchmark Engine:

$$
T_{\mathrm{interaction}} = \sum_{i=1}^{n} 1 = n
$$

Trong đó, $T_{\mathrm{interaction}}$ là tổng số lượt gọi công cụ được ghi nhận và $n$ là số bản ghi đáp ứng quy tắc đếm. Chỉ số này hỗ trợ phân tích mức độ tương tác giữa Agent và công cụ mạng trong quá trình xử lý nhiệm vụ.

Việc kết hợp các tiêu chí trên cho phép đánh giá hệ thống Multi-Agent trên nhiều phương diện, bao gồm khả năng hoàn thành nhiệm vụ, độ chính xác của kết quả chẩn đoán, hiệu quả khắc phục sự cố, mức độ an toàn và hiệu năng thực thi. Các tiêu chí này là cơ sở để xây dựng phương pháp thực nghiệm, tổng hợp số liệu và phân tích kết quả đánh giá hệ thống trong các chương tiếp theo.

---

# CHƯƠNG 3. PHÂN TÍCH, THIẾT KẾ VÀ XÂY DỰNG HỆ THỐNG

## 3.1. Phương pháp nghiên cứu

### 3.1.1. Phương pháp nghiên cứu tài liệu

**Mục đích.** Xây dựng cơ sở lý thuyết cho đề tài, tìm hiểu các phương pháp đã được nghiên cứu và xác định hướng tiếp cận phù hợp để xây dựng hệ thống Multi-Agent hỗ trợ cấu hình và xử lý sự cố mạng.

**Nội dung thực hiện.** Thu thập, khảo sát và phân tích các công trình khoa học liên quan đến Large Language Model, AI Agent, Multi-Agent System, Network Automation và Network Troubleshooting. Quá trình phân tích tập trung vào kiến trúc hệ thống, phương pháp tương tác với thiết bị mạng, cơ chế phối hợp giữa các agent, kết quả đạt được và hạn chế của các nghiên cứu trước đó.

**Kết quả.** Cơ sở lý thuyết và tổng quan nghiên cứu được tổng hợp tại Chương 1 và Chương 2. Kết quả khảo sát là căn cứ lựa chọn kiến trúc điều phối tập trung, phân chia vai trò giữa các agent, sử dụng công cụ mạng để tương tác với môi trường và áp dụng cơ chế kiểm soát đối với hành động cấu hình.

### 3.1.2. Phương pháp phân tích và thiết kế hệ thống

**Mục đích.** Xác định các yêu cầu của hệ thống, phân chia trách nhiệm giữa các thành phần và xây dựng kiến trúc Multi-Agent phù hợp với các tác vụ cấu hình, chẩn đoán và khắc phục sự cố mạng.

**Nội dung thực hiện.** Phân tích quy trình quản trị mạng, xác định các chức năng chính và phân bổ nhiệm vụ cho các agent chuyên trách. Thiết kế cơ chế điều phối, phương thức trao đổi thông tin và luồng xử lý yêu cầu giữa các thành phần. UML được sử dụng để mô tả tác nhân, chức năng và hoạt động của hệ thống thông qua use-case diagram và activity diagram.

**Kết quả.** Kiến trúc tổng thể, đặc tả chức năng của từng agent, sơ đồ tương tác và quy trình xử lý các nhiệm vụ quản trị mạng được trình bày trong các mục tiếp theo của Chương 3.

### 3.1.3. Phương pháp xây dựng hệ thống

**Mục đích.** Hiện thực hóa kiến trúc Multi-Agent đã thiết kế, xây dựng hệ thống có khả năng tiếp nhận yêu cầu bằng ngôn ngữ tự nhiên và hỗ trợ quản trị viên thực hiện các tác vụ trên thiết bị mạng trong môi trường mô phỏng.

**Nội dung thực hiện.** Sử dụng Python và LangGraph để phát triển các agent và tổ chức quy trình phối hợp giữa chúng. Tích hợp LLM để phân tích yêu cầu và hỗ trợ đưa ra quyết định. Sử dụng Netmiko, Nornir và SSH/Telnet để thu thập thông tin, thực thi các lệnh kiểm tra và cấu hình trên thiết bị mạng.

Các thành phần chức năng gồm Planning Orchestrator, Configuration Orchestrator, Execution Orchestrator, Analysis Orchestrator cùng Planner Agent, Configuration Agent, Network Agent và Analyst Agent. Hệ thống còn sử dụng diagnostic playbook, bộ phân tích evidence, Evidence Coverage Gate và Causal Evidence Gate để hỗ trợ quá trình chẩn đoán. Cơ chế Human-in-the-loop được tích hợp để quản trị viên xem xét và phê duyệt các thay đổi cấu hình trước khi thực thi. Backend sử dụng FastAPI và PostgreSQL; frontend sử dụng React và TypeScript để cung cấp giao diện quản trị, hội thoại, theo dõi tác vụ, phê duyệt và đánh giá benchmark.

**Kết quả.** Hệ thống Multi-Agent có khả năng tương tác với môi trường mạng GNS3 và thực hiện các chức năng cấu hình, chẩn đoán và hỗ trợ khắc phục sự cố.

### 3.1.4. Phương pháp thực nghiệm

**Mục đích.** Kiểm tra khả năng hoạt động của hệ thống Multi-Agent trong các tình huống quản trị mạng cụ thể, xác định mức độ đáp ứng yêu cầu chức năng và thu thập dữ liệu phục vụ đánh giá.

**Nội dung thực hiện.** Xây dựng topology mạng trong GNS3 và thiết lập các kịch bản kiểm thử với trạng thái ban đầu, thao tác tiêm lỗi, Ground Truth, điều kiện xác minh và thao tác cleanup được xác định trước. Các kịch bản được thực hiện trong điều kiện tương đương; hệ thống ghi nhận kết quả chẩn đoán, thời gian thực thi, số lượt tương tác và dấu vết hoạt động của các agent.

**Kết quả.** Bộ dữ liệu thực nghiệm gồm Benchmark Scenario, Benchmark Run, Task, Execution, Evaluation và các chỉ số quan sát. Kết quả tổng hợp được trình bày tại Chương 4.

### 3.1.5. Phương pháp đánh giá

**Mục đích.** Đánh giá mức độ hoàn thành các mục tiêu nghiên cứu, xác định khả năng, hiệu quả và những hạn chế của hệ thống Multi-Agent trong các nhiệm vụ cấu hình và xử lý sự cố mạng.

**Nội dung thực hiện.** Kết hợp đánh giá định lượng và phân tích định tính. Các chỉ số đã được triển khai gồm Task Success Rate, Detection Score, Localization Precision/Recall/F1, Fault Type Precision/Recall/F1, RCA Precision/Recall/F1, Active Workflow Latency và Interaction Turns. Remediation Success Rate và Safety được giữ trong mô hình đánh giá nhưng chưa có scorer độc lập nên được phân loại `NOT_APPLICABLE`. Cách lựa chọn tiêu chí tham khảo phương pháp đánh giá AI Agent trong NIKA [3], NETARENA [4] và NetConfArena [5]. Phân tích định tính tập trung vào bằng chứng thu thập được, nguyên nhân của trường hợp thất bại, khả năng kiểm soát thao tác ghi và giới hạn của môi trường thực nghiệm.

**Kết quả.** Các bảng số liệu, biểu đồ và nhận xét đánh giá phản ánh khả năng hoàn thành nhiệm vụ, độ chính xác, tính an toàn, hiệu năng và hạn chế của hệ thống.

## 3.2. Phân tích yêu cầu hệ thống

### 3.2.1. Các tác nhân và phạm vi sử dụng

Hệ thống được xây dựng nhằm hỗ trợ người quản trị thực hiện các nhiệm vụ quản lý tài nguyên, cấu hình, kiểm tra và xử lý sự cố trên thiết bị mạng. Các chức năng đã triển khai được tổ chức thành các nhóm: tổng quan và thống kê; hội thoại với hệ thống Multi-Agent; theo dõi Task và phê duyệt thao tác cấu hình; quản lý thiết bị, credential và danh mục thiết bị; quản lý Benchmark Scenario, Benchmark Run và Evaluation; quản lý Audit Log; quản lý người dùng, vai trò và quyền truy cập; tùy chọn giao diện và ngôn ngữ phía người dùng.

Tác nhân con người của hệ thống là **người dùng đã được xác thực**. Phạm vi thao tác của từng người dùng không được gắn cứng tại giao diện mà được xác định bằng cơ chế Role-Based Access Control (RBAC), dựa trên vai trò, chức năng quản lý và hành động được cấp. Dữ liệu seed hiện định nghĩa bốn vai trò gồm **Super Administrator**, **System Administrator**, **Network Engineer** và **Network Operator**. Trong đó, Super Administrator phục vụ quản trị toàn bộ nền tảng; các vai trò còn lại được cấp quyền theo ma trận permission và có thể được điều chỉnh tại chức năng Access Control. Vì quyền của vai trò có thể thay đổi, tên vai trò chỉ biểu thị nhóm trách nhiệm, còn quyền truy cập thực tế phải được xác định từ dữ liệu phân quyền tại thời điểm xử lý yêu cầu.

Ngoài người dùng, hệ thống tương tác với ba nhóm tác nhân kỹ thuật bên ngoài. **Dịch vụ LLM** tiếp nhận prompt có kiểm soát và trả về kế hoạch nghiệp vụ, CLI cấu hình hoặc kết quả phân tích có cấu trúc tùy theo Agent gọi mô hình. **GNS3 API** cung cấp thông tin project, node và môi trường topology phục vụ thực nghiệm. **Thiết bị mạng trong GNS3** tiếp nhận kết nối SSH/Telnet từ NetworkTool để thực thi lệnh kiểm tra hoặc cấu hình. Thông tin xác thực thiết bị được lấy từ Credential Service và chỉ được chuyển đến lớp công cụ mạng khi thực thi; credential không được cung cấp trực tiếp cho LLM.

Planner Agent, Configuration Agent, Network Agent, Analyst Agent, các Orchestrator và Benchmark Engine là các thành phần xử lý **nội bộ**, không phải người dùng độc lập của hệ thống. Planner Agent sử dụng yêu cầu, inventory công khai, topology và diagnostic playbook để tạo kế hoạch nghiệp vụ. Configuration Agent chuyển `configuration_requirements` của Operation WRITE thành CLI nhưng không kết nối thiết bị. Network Agent thực thi Operation thông qua NetworkTool sau khi vượt qua các điều kiện phụ thuộc và Approval Gate. Analyst Agent phân tích kết quả thực thi và bằng chứng thu thập được. Các Orchestrator điều phối trạng thái workflow, còn Benchmark Engine quản lý việc tiêm lỗi, xác minh, đánh giá và cleanup theo Scenario. Việc phân tách này ngăn Agent tự do truy cập cơ sở dữ liệu, credential hoặc thiết bị ngoài phạm vi đã được service kiểm soát.

Phạm vi triển khai của đề tài được giới hạn trong môi trường mạng mô phỏng GNS3 có kiểm soát. Các thao tác WRITE phải được người dùng có quyền phê duyệt trước khi thực thi. Hoạt động điều tra bổ sung chỉ sử dụng thao tác READ; hoạt động tiêm lỗi và cleanup chỉ được thực hiện trong quy trình benchmark. Hệ thống chưa được thiết kế để tự động vận hành mạng production hoặc tự quyết định mọi thay đổi cấu hình mà không có sự giám sát của con người.

```mermaid
flowchart LR
    subgraph ACTORS[Người dùng đã xác thực]
        SA[Super Administrator]
        SYSA[System Administrator]
        NE[Network Engineer]
        NO[Network Operator]
    end

    subgraph SYSTEM[Hệ thống Network Multi-Agent]
        RBAC[Authentication và RBAC]
        ADMIN[Users, Roles, Access Control và Settings]
        INVENTORY[Devices, Credentials và Device Catalog]
        CHAT[Chat và Conversation]
        TASK[Task, Operation, Approval và Activity]
        MAS[Orchestrator, Planner, Configuration, Network và Analyst Agent]
        BENCH[Benchmark Scenario và Benchmark Run]
        EVAL[Evaluation và Dashboard]
        AUDIT[Audit Log]
    end

    subgraph EXTERNAL[Tác nhân kỹ thuật bên ngoài]
        LLM[Dịch vụ LLM]
        GNS3[GNS3 API]
        DEV[Thiết bị mạng trong GNS3]
    end

    SA --> RBAC
    SYSA --> RBAC
    NE --> RBAC
    NO --> RBAC

    RBAC -->|Kiểm tra permission| ADMIN
    RBAC -->|Kiểm tra permission| INVENTORY
    RBAC -->|Kiểm tra permission| CHAT
    RBAC -->|Kiểm tra permission| TASK
    RBAC -->|Kiểm tra permission| BENCH
    RBAC -->|Kiểm tra permission| EVAL
    RBAC -->|Kiểm tra permission| AUDIT

    CHAT -->|Tạo yêu cầu| TASK
    TASK -->|Điều phối workflow| MAS
    MAS <-->|Prompt và structured output| LLM
    MAS -->|Đọc inventory công khai| INVENTORY
    MAS -->|SSH hoặc Telnet qua NetworkTool| DEV
    BENCH <-->|Project, node và topology| GNS3
    BENCH -->|Tiêm lỗi, xác minh và cleanup| DEV
    BENCH -->|Tạo Task chẩn đoán| TASK
    TASK --> EVAL
    ADMIN --> AUDIT
    INVENTORY --> AUDIT
    TASK --> AUDIT
```

_Hình 3.1. Sơ đồ tác nhân, phạm vi chức năng và các hệ thống bên ngoài theo triển khai thực tế._

### 3.2.2. Yêu cầu chức năng

Yêu cầu chức năng xác định những khả năng hệ thống cung cấp cho người dùng trong phạm vi quyền được cấp. Các yêu cầu được tổ chức theo các nhóm nghiệp vụ đã triển khai trên frontend và backend.

1. **Quản lý danh tính và quyền truy cập (Identity and Access Management)** <br> Hệ thống hỗ trợ đăng nhập, làm mới token, đăng xuất, quản lý session, người dùng, vai trò và ma trận permission. Mỗi permission được xác định theo cặp chức năng–hành động và được gán cho vai trò. Identity Service xác thực access token, kiểm tra session, trạng thái tài khoản và quyền trước khi cho phép thực hiện nghiệp vụ được bảo vệ.

2. **Quản lý thiết bị và thông tin kết nối (Device Inventory and Credential Management)** <br> Hệ thống cho phép quản lý thiết bị, brand, category, Netmiko driver và credential. Credential được lưu ở dạng mã hóa và chỉ được giải mã trong quá trình chuẩn bị kết nối. Inventory cung cấp thông tin thiết bị công khai cho Planner và thông tin kết nối cần thiết cho NetworkTool.

3. **Tương tác với AI Agent (Natural Language Interaction)** <br> Người dùng có thể gửi yêu cầu bằng ngôn ngữ tự nhiên, xem và đổi tên hội thoại, theo dõi Activity Timeline, yêu cầu phê duyệt và phản hồi cuối. Mỗi USER_REQUEST hợp lệ có thể tạo một Task gồm nhiều Operation; frontend nhận Task Activity gần thời gian thực qua Server-Sent Events (SSE), sử dụng REST API để tải dữ liệu chi tiết và chuyển sang polling dự phòng khi stream không khả dụng.

4. **Lập kế hoạch và điều phối tác vụ (Task Planning and Orchestration)** <br> Agent chuyển yêu cầu thành Execution Plan có cấu trúc, gồm các Operation, thông tin thiết bị và quan hệ phụ thuộc. Các quan hệ được tổ chức theo Directed Acyclic Graph (DAG). Kế hoạch phải được kiểm tra tính hợp lệ trước khi lưu trữ và thực thi.

5. **Thực thi tác vụ mạng (Network Task Execution)** <br> Network Agent thực thi các Operation thông qua NetworkTool sử dụng backend Netmiko hoặc Nornir theo cấu hình. Hệ thống phân biệt thao tác READ để thu thập thông tin và WRITE để thay đổi cấu hình. Quá trình thực thi tuân thủ dependency, lưu Execution và Device Action Log, đồng thời cập nhật trạng thái Task, Operation và mapping thiết bị.

6. **Phê duyệt và kiểm soát cấu hình (Approval and Execution Control)** <br> Các thao tác ghi phải được phê duyệt trước khi thực thi. Hệ thống sử dụng Approval Gate để kiểm tra trạng thái phê duyệt, Commands Snapshot và SHA-256 Request Hash nhằm bảo đảm nội dung lệnh không bị thay đổi sau khi được chấp thuận. Hệ thống hỗ trợ xử lý yêu cầu bị từ chối, hết hạn và tiếp tục Task sau khi có quyết định hợp lệ.

7. **Phân tích và chẩn đoán sự cố mạng (Network Diagnosis and Root Cause Analysis)** <br> Analyst Agent phân tích output thực thi, nhận diện bất thường và trả kết luận có cấu trúc gồm trạng thái sự cố, vị trí và loại nguyên nhân. Khi bằng chứng chưa đầy đủ, workflow thực hiện Evidence-Guided Investigation bằng các Operation READ-only trong giới hạn số vòng cấu hình. Evidence Coverage và Causal Evidence Gate được sử dụng để phân biệt root cause đã được xác nhận với suspected cause hoặc trường hợp chưa đủ dữ liệu.

8. **Quản lý lịch sử và nhật ký (Task Tracking and Audit Logging)** <br> Hệ thống lưu trữ thông tin Task, Operation, Execution, Device Action Log và Task Activity Event nhằm theo dõi toàn bộ quá trình xử lý. Bên cạnh đó, Audit Log ghi nhận những hoạt động nghiệp vụ quan trọng để hỗ trợ kiểm tra, tìm kiếm và truy vết.

9. **Quản lý thực nghiệm và đánh giá (Benchmark and Evaluation)** <br> Hệ thống hỗ trợ tạo và cập nhật Benchmark Scenario, chạy Benchmark Run, đóng băng scenario snapshot, kiểm tra precondition, tiêm lỗi, xác minh, liên kết Task, chấm Evaluation và cleanup môi trường. Ground Truth được tách khỏi dữ liệu cung cấp cho Agent. Kết quả được đánh giá bằng Detection, Localization, Fault Type, Structured RCA, Task Success Rate, Latency và Interaction Turns.

10. **Thống kê và trình bày kết quả (Dashboard and Reporting)** <br> Hệ thống tổng hợp dữ liệu thiết bị, Task, trạng thái thực thi và Benchmark Evaluation để hiển thị các chỉ số và biểu đồ trên Dashboard. Người dùng có thể lọc dữ liệu đánh giá theo thời gian, theo dõi Task Outcome và xu hướng thời gian thực thi.

### 3.2.3. Yêu cầu phi chức năng

Yêu cầu phi chức năng xác định các đặc tính chất lượng cần đáp ứng trong quá trình xây dựng và vận hành hệ thống. Đối với hệ thống Multi-Agent hỗ trợ quản trị mạng, các yêu cầu này tập trung vào bảo mật, tính an toàn, độ tin cậy, hiệu năng và khả năng bảo trì.

1. **Bảo mật và kiểm soát truy cập (Security and Access Control)** <br> Hệ thống phải xác thực access token, kiểm tra session và quyền RBAC trước khi thực hiện thao tác được bảo vệ. Mật khẩu người dùng được băm; refresh token được lưu dưới dạng hash và được xoay khi làm mới phiên. Credential thiết bị được mã hóa, còn khóa API và các bí mật cấu hình chỉ được quản lý tại backend, không chuyển xuống frontend hoặc cung cấp trực tiếp cho LLM.

2. **Tính toàn vẹn và nhất quán dữ liệu (Data Integrity and Consistency)** <br> PostgreSQL là nguồn dữ liệu chuẩn cho vòng đời Conversation, Task, Operation, Approval, Execution, Benchmark và Evaluation. Những cập nhật liên quan phải sử dụng transaction và khóa dữ liệu khi cần thiết. Commands Snapshot và Request Hash được kiểm tra để bảo đảm nội dung thực thi không khác nội dung đã được phê duyệt; LangGraph state không thay thế dữ liệu nghiệp vụ đã lưu.

3. **Tính an toàn trong thực thi (Execution Safety)** <br> Hệ thống phải phân biệt rõ thao tác READ và WRITE. Các lệnh WRITE chỉ được thực hiện sau khi vượt qua Approval Gate, trong khi những yêu cầu chưa được duyệt, bị từ chối hoặc hết hạn phải được ngăn thực thi. Các thao tác điều tra bổ sung được giới hạn ở chế độ READ nhằm hạn chế thay đổi ngoài ý muốn.

4. **Độ tin cậy và xử lý lỗi (Reliability and Fault Handling)** <br> Hệ thống phải phát hiện và ghi nhận lỗi gọi LLM, structured output không hợp lệ, lỗi kết nối thiết bị và lỗi CLI. Timeout, retry và schema validation được áp dụng tại các vị trí phù hợp. Khi một Operation thất bại, dependency được xử lý theo điều kiện đã xác định. Benchmark cleanup có retry và bước xác minh để tránh ghi nhận môi trường đã khôi phục khi trạng thái thiết bị chưa đúng.

5. **Hiệu năng (Performance)** <br> Hệ thống cần kiểm soát timeout của LLM và thiết bị, đồng thời tách những thao tác mạng đồng bộ khỏi luồng xử lý bất đồng bộ khi cần thiết. Thời gian hoạt động của AI workflow được ghi nhận riêng với thời gian chờ phê duyệt của người dùng. Backend hỗ trợ API phân trang và summary phía server, nhưng Dashboard hiện còn tải toàn bộ các trang Task/Evaluation/Run phục vụ một số biểu đồ. Server-side aggregation cho các biểu đồ này là mục tiêu tối ưu khi dữ liệu tăng.

6. **Khả năng quan sát và truy vết (Observability and Traceability)** <br> Các sự kiện quan trọng trong vòng đời Task phải được ghi nhận thông qua Activity Event, Execution, Device Action Log và Audit Log. Benchmark Run phải liên kết được với Scenario snapshot, Conversation, Task và Evaluation. Dữ liệu cần hỗ trợ truy xuất quá trình lập kế hoạch, thực thi, phê duyệt, phân tích và cleanup.

7. **Khả năng bảo trì và mở rộng (Maintainability and Extensibility)** <br> Hệ thống được tổ chức theo các lớp trình bày, API, Core Domain Services, AI và điều phối, tích hợp và lưu trữ. Backend phân chia domain theo module; NetworkTool trừu tượng hóa Netmiko/Nornir; các lớp tích hợp cô lập LLM và GNS3. Cấu trúc này hạn chế phụ thuộc trực tiếp và hỗ trợ thay đổi công nghệ hoặc bổ sung chức năng.

8. **Khả năng sử dụng (Usability)** <br> Giao diện phải được tổ chức thống nhất, hỗ trợ tiếng Việt và tiếng Anh, hiển thị rõ trạng thái Task, tiến trình Agent, yêu cầu phê duyệt và kết quả benchmark. Các biểu mẫu, bộ lọc, phân trang và thông báo lỗi cần giúp người dùng nhận biết trạng thái hiện tại và hành động tiếp theo.

9. **Khả năng kiểm thử và tái lập (Testability and Reproducibility)** <br> Mỗi Benchmark Scenario phải xác định precondition, thao tác tiêm lỗi, điều kiện xác minh, Ground Truth và cleanup. Benchmark Run lưu snapshot của phiên bản Scenario tại thời điểm bắt đầu để tránh thay đổi dữ liệu đánh giá giữa chừng. Mỗi lượt chạy được lưu độc lập và chỉ kết thúc cleanup sau khi trạng thái khôi phục đã được kiểm chứng.

## 3.3. Công nghệ và môi trường triển khai

### 3.3.1. LangGraph

LangGraph được sử dụng làm framework điều phối quy trình xử lý của hệ thống Multi-Agent, hỗ trợ tổ chức và quản lý sự phối hợp giữa các AI Agent. Framework này cung cấp mô hình đồ thị trạng thái (State Graph), trong đó các nút (node) biểu diễn những bước xử lý, còn các cạnh (edge) xác định luồng chuyển tiếp. Cơ chế này cho phép tổ chức quy trình nhiều giai đoạn, hỗ trợ rẽ nhánh có điều kiện và duy trì thông tin trạng thái trong suốt quá trình thực thi.

Trong hệ thống, LangGraph tổ chức các bước xử lý chính, bao gồm kiểm tra môi trường GNS3, phân tích yêu cầu, lập kế hoạch, sinh cấu hình cho Operation WRITE, tương tác với thiết bị mạng và phân tích kết quả thực thi. Các thành phần trao đổi thông tin thông qua trạng thái dùng chung, đồng thời lựa chọn hướng xử lý dựa trên kết quả của những bước trước đó. Đối với nhiệm vụ chẩn đoán sự cố, quy trình có thể chuyển sang bước điều tra bổ sung khi thông tin ban đầu chưa đủ để xác định nguyên nhân. Việc sử dụng LangGraph giúp quản lý luồng xử lý rõ ràng và tạo điều kiện mở rộng các chức năng của hệ thống.

### 3.3.2. Netmiko và Nornir

Netmiko và Nornir được sử dụng để hỗ trợ tương tác và tự động hóa thao tác trên thiết bị mạng. Trong đó, Netmiko đảm nhiệm việc thiết lập kết nối SSH, gửi lệnh và thu thập kết quả thông qua giao diện dòng lệnh (Command-Line Interface – CLI). Nornir cung cấp các thành phần quản lý danh sách thiết bị (Inventory), tổ chức tác vụ và hỗ trợ thực thi trên nhiều thiết bị theo quy trình thống nhất.

Trong kiến trúc backend, hệ thống xây dựng lớp `NetworkTool` nhằm trừu tượng hóa quá trình tương tác với thiết bị mạng. Tùy theo cấu hình, lớp này có thể sử dụng Netmiko trực tiếp hoặc kết hợp Nornir với plugin Netmiko để thực hiện các tác vụ kiểm tra trạng thái và thay đổi cấu hình. `NetworkTool` cung cấp giao diện thực thi thống nhất cho các thành phần xử lý nghiệp vụ và AI Agent, giúp hạn chế sự phụ thuộc vào chi tiết triển khai của từng thư viện.

Việc tách biệt lớp tương tác thiết bị khỏi logic điều phối giúp nâng cao tính mô-đun, thuận tiện cho quá trình bảo trì và mở rộng hệ thống. Đồng thời, cách tổ chức này cho phép thay đổi hoặc bổ sung phương thức kết nối thiết bị mà không cần điều chỉnh đáng kể các thành phần Multi-Agent.

### 3.3.3. GNS3 và môi trường giả lập mạng

GNS3 (Graphical Network Simulator 3) được sử dụng để xây dựng môi trường mạng phục vụ phát triển, kiểm thử và đánh giá hệ thống. Nền tảng này cho phép thiết lập các topology gồm thiết bị định tuyến, chuyển mạch và những liên kết mạng thông qua môi trường ảo hóa, giúp thực hiện các thao tác cấu hình và chẩn đoán mà không ảnh hưởng đến hạ tầng mạng thực tế.

Trong phạm vi đề tài, các topology được thiết kế để mô phỏng những tình huống vận hành và sự cố như sai cấu hình địa chỉ IP, giao diện bị vô hiệu hóa hoặc thông tin định tuyến không chính xác. Mỗi kịch bản thực nghiệm được xác định dựa trên trạng thái ban đầu, nguyên nhân sự cố và kết quả mong đợi. Môi trường GNS3 cho phép tái tạo các điều kiện thử nghiệm, hỗ trợ kiểm tra và đánh giá kết quả xử lý theo những tiêu chí được thiết lập trước.

Backend tích hợp GNS3 Provider để giao tiếp với GNS3 Server, kiểm tra khả năng truy cập và khai thác thông tin topology phục vụ quá trình chẩn đoán. Trong khi GNS3 Provider đảm nhiệm tương tác với môi trường mô phỏng, các thao tác kiểm tra trạng thái và thay đổi cấu hình bên trong thiết bị được thực hiện thông qua lớp `NetworkTool`. Sự phân tách này giúp xác định rõ trách nhiệm của từng thành phần và bảo đảm tính độc lập giữa quản lý môi trường mạng và thực thi lệnh trên thiết bị.

### 3.3.4. Các công nghệ phát triển ứng dụng

Hệ thống được phát triển theo kiến trúc phân tách frontend và backend, kết hợp với cơ sở dữ liệu quan hệ và dịch vụ cung cấp mô hình ngôn ngữ lớn. Các công nghệ được lựa chọn nhằm bảo đảm tính mô-đun, thuận tiện cho quá trình phát triển, kiểm thử, bảo trì và mở rộng hệ thống.

Về phía frontend, ứng dụng sử dụng React kết hợp TypeScript để xây dựng giao diện theo hướng thành phần và hỗ trợ kiểm tra kiểu dữ liệu. Vite được sử dụng để thiết lập môi trường phát triển, React Router đảm nhiệm điều hướng giữa các trang, trong khi Tailwind CSS và shadcn/ui hỗ trợ xây dựng giao diện nhất quán, có khả năng tái sử dụng. Thư viện Axios được tích hợp để thực hiện các yêu cầu HTTP và trao đổi dữ liệu với backend.

Về phía backend, hệ thống được xây dựng bằng Python với framework FastAPI, cung cấp các REST API nghiệp vụ thông qua tiền tố /api/v1. FastAPI đảm nhiệm tiếp nhận yêu cầu, điều phối đến các thành phần xử lý nghiệp vụ và trả về kết quả tương ứng. Thư viện Pydantic được sử dụng để định nghĩa cấu trúc dữ liệu và kiểm tra tính hợp lệ của dữ liệu đầu vào, đầu ra, bảo đảm tính nhất quán trong quá trình giao tiếp giữa các thành phần.

Về cơ sở dữ liệu, PostgreSQL được sử dụng để lưu trữ thông tin thiết bị mạng, nhiệm vụ, trạng thái thực thi, lịch sử hoạt động và kết quả thực nghiệm. Backend tích hợp SQLAlchemy để ánh xạ các mô hình dữ liệu với bảng quan hệ, đồng thời hỗ trợ truy vấn và cập nhật dữ liệu. Cách tổ chức này giúp tách biệt lớp truy cập dữ liệu khỏi logic nghiệp vụ và thuận tiện cho việc bảo trì hệ thống.
Về tích hợp mô hình ngôn ngữ lớn, backend sử dụng LangChain kết hợp NVIDIA AI Endpoint để tương tác với các mô hình LLM đã được huấn luyện sẵn. LangChain hỗ trợ tổ chức thông điệp, gửi yêu cầu và xử lý phản hồi từ mô hình, phục vụ Planner Agent trong lập kế hoạch, Configuration Agent trong sinh CLI WRITE và Analyst Agent trong phân tích kết quả thực thi. Việc sử dụng API cho phép hệ thống khai thác khả năng của LLM mà không cần triển khai mô hình trực tiếp trên hạ tầng cục bộ.

Về môi trường triển khai, Docker Compose được sử dụng để tổ chức các dịch vụ backend, PostgreSQL và pgAdmin trong quá trình phát triển và kiểm thử. Công cụ này hỗ trợ quản lý cấu hình, kết nối và các thành phần phụ thuộc giữa những container. Trong đó, pgAdmin phục vụ việc quản lý và kiểm tra dữ liệu PostgreSQL. Cách triển khai này giúp đơn giản hóa quá trình khởi tạo và bảo đảm tính nhất quán của môi trường kiểm thử.

## 3.4. Thiết kế kiến trúc tổng thể hệ thống

### 3.4.1. Kiến trúc tổng thể

Hệ thống Multi-Agent hỗ trợ cấu hình và xử lý sự cố mạng được xây dựng theo kiến trúc phân lớp. Kiến trúc tổng thể gồm lớp trình bày, lớp API, các dịch vụ nghiệp vụ cốt lõi, thành phần điều phối Multi-Agent, lớp tích hợp và lớp lưu trữ. Cách tổ chức này phân tách trách nhiệm giữa giao diện người dùng, xử lý nghiệp vụ, suy luận bằng LLM, tương tác thiết bị và quản lý dữ liệu.

Người dùng truy cập hệ thống thông qua ứng dụng web React/TypeScript. Phạm vi chức năng của Super Administrator, System Administrator, Network Engineer và Network Operator được xác định bằng RBAC. Frontend giao tiếp với FastAPI qua REST API và SSE trên nền HTTP, không truy cập trực tiếp cơ sở dữ liệu, LLM hoặc thiết bị mạng.

Backend FastAPI cung cấp API cho các dịch vụ cốt lõi đã triển khai, gồm Identity và Access Control, Inventory và Credential, Conversation và Task Execution, Benchmark và Evaluation, Audit Log. Identity Service thực hiện xác thực, quản lý session và kiểm tra quyền. Các dịch vụ nghiệp vụ sử dụng Persistence Layer dựa trên SQLAlchemy để đọc và ghi PostgreSQL.

Thành phần Multi-Agent sử dụng LangGraph và Orchestrator để phối hợp Planner Agent, Configuration Agent, Network Agent và Analyst Agent. Planner, Configuration và Analyst tương tác với NVIDIA AI Endpoint thông qua lớp tích hợp LLM. Workflow kiểm tra GNS3 Server thông qua lớp tích hợp GNS3, trong khi Network Agent sử dụng lớp tích hợp thiết bị dựa trên Netmiko hoặc Nornir để thực thi lệnh. Benchmark Service cũng sử dụng lớp tích hợp thiết bị để kiểm tra baseline, tiêm lỗi, xác minh và cleanup. Các kết nối đến thiết bị được thực hiện qua SSH hoặc Telnet trong phạm vi inventory và credential đã quản lý.

FastAPI API, Workflow Worker riêng, PostgreSQL và pgAdmin được triển khai bằng Docker Compose trong môi trường phát triển và thực nghiệm. API lưu yêu cầu và đưa Workflow Job vào hàng đợi bền vững trên PostgreSQL; Worker nhận job và chạy LangGraph ngoài vòng đời request HTTP. Frontend chạy riêng và kết nối qua REST API và SSE. Phiên bản hiện tại không sử dụng Redis, message broker ngoài PostgreSQL hoặc WebSocket.

```mermaid
flowchart TB
    ACTOR["Người dùng<br/>Super Administrator · System Administrator<br/>Network Engineer · Network Operator"]
    subgraph SYSTEM["HỆ THỐNG NETWORK MULTI-AGENT"]
        subgraph PRESENTATION["Lớp trình bày"]
            FE["Web Application<br/>React · TypeScript"]
        end
        subgraph API_LAYER["Lớp API"]
            API["FastAPI<br/>REST API · SSE"]
        end
        subgraph CORE["Dịch vụ nghiệp vụ"]
            IDENTITY["Identity · Session · RBAC"]
            INVENTORY["Inventory · Credential"]
            EXEC_DOMAIN["Conversation · Task Execution"]
            BENCHMARK["Benchmark · Evaluation"]
            AUDIT["Audit Log"]
        end
        subgraph AI["Lớp điều phối và AI"]
            WORKER["Workflow Worker<br/>Claim · Retry · Recover"]
            GRAPH["LangGraph<br/>Planning · Configuration · Execution · Analysis"]
            AGENTS["Planner · Configuration · Network · Analyst"]
        end
        subgraph INTEGRATION["Lớp tích hợp"]
            LLMINT["LLM Integration"]
            GNS3INT["GNS3 Integration"]
            NETINT["NetworkTool<br/>Netmiko · Nornir"]
        end
        subgraph DATA["Lớp lưu trữ"]
            PERSISTENCE["SQLAlchemy · Repository"]
            DB[("PostgreSQL<br/>Business State · Workflow Jobs · Task Activity")]
        end
        DEPLOY["Docker Compose<br/>API · Workflow Worker · DB · pgAdmin"]
    end
    subgraph EXTERNAL["Dịch vụ và môi trường bên ngoài"]
        LLM["NVIDIA AI Endpoint"]
        GNS3["GNS3 Server / API"]
        DEV["Thiết bị mạng GNS3"]
    end
    ACTOR --> FE
    FE <-->|REST / SSE| API
    API --> IDENTITY
    API --> INVENTORY
    API --> EXEC_DOMAIN
    API --> BENCHMARK
    API --> AUDIT
    API -->|"Enqueue Message / Approval Job"| DB
    DB <-->|"Claim · Complete · Retry"| WORKER
    WORKER --> GRAPH
    GRAPH --> AGENTS
    GRAPH --> EXEC_DOMAIN
    GRAPH --> INVENTORY
    GRAPH --> GNS3INT
    AGENTS --> LLMINT
    AGENTS --> NETINT
    BENCHMARK -->|"Precondition · Injection · Cleanup"| NETINT
    IDENTITY --> PERSISTENCE
    INVENTORY --> PERSISTENCE
    EXEC_DOMAIN --> PERSISTENCE
    BENCHMARK --> PERSISTENCE
    AUDIT --> PERSISTENCE
    PERSISTENCE <-->|SQL| DB
    DB -->|"Activity: LISTEN / NOTIFY"| API
    DEPLOY -.-> API
    DEPLOY -.-> WORKER
    DEPLOY -.-> DB
    LLMINT <-->|HTTPS| LLM
    GNS3INT <-->|REST| GNS3
    NETINT <-->|SSH / Telnet| DEV
```

_Hình 3.2. Sơ đồ kiến trúc tổng thể của hệ thống Network Multi-Agent theo các thành phần đã triển khai._

### 3.4.2. Các thành phần chức năng và mối quan hệ

Kiến trúc hệ thống gồm các thành phần chức năng được tổ chức theo từng lớp như Hình 3.2.

**Lớp trình bày (Presentation Layer).** Web Application được xây dựng bằng React và TypeScript, cung cấp giao diện đăng nhập, Dashboard, hội thoại với AI, theo dõi Task, phê duyệt thay đổi cấu hình, quản lý thiết bị và credential, quản lý Benchmark Scenario và Benchmark Run, xem Evaluation, Audit Log, người dùng và quyền truy cập. Frontend chịu trách nhiệm hiển thị dữ liệu và tiếp nhận thao tác của người dùng, nhưng không trực tiếp thực hiện nghiệp vụ, truy vấn PostgreSQL hoặc kết nối thiết bị mạng.

**Lớp API (API Layer).** FastAPI cung cấp các REST API và endpoint SSE dưới tiền tố `/api/v1`, tiếp nhận yêu cầu HTTP từ frontend, kiểm tra cấu trúc dữ liệu đầu vào và chuyển yêu cầu đến thành phần xử lý phù hợp. API Layer không chứa nghiệp vụ xác thực hoặc phân quyền; các router sử dụng Identity Service để xác thực phiên và kiểm tra permission trước khi gọi Core Domain Services. Đối với yêu cầu hội thoại hoặc tiếp tục Task sau phê duyệt, API Layer ghi Workflow Job vào PostgreSQL; Workflow Worker thực thi Multi-Agent Workflow bất đồng bộ. Endpoint SSE phát lại Task Activity đã lưu và truyền sự kiện mới cho frontend.

**Các dịch vụ nghiệp vụ cốt lõi (Core Domain Services).** Các nghiệp vụ của hệ thống được phân chia theo domain:

- **Identity & Access** quản lý người dùng, vai trò, permission, mật khẩu, access token, refresh token và vòng đời session; thực hiện Authentication và RBAC.
- **Inventory & Credential** quản lý thiết bị, brand, category, thông tin kết nối và credential đã mã hóa; cung cấp ngữ cảnh thiết bị cho quá trình lập kế hoạch và thực thi.
- **Conversation & Task Execution** quản lý hội thoại, message, Task, Operation, dependency, ánh xạ thiết bị, Approval, Execution, Activity và Device Action Log.
- **Benchmark & Evaluation** quản lý Scenario, Run, Ground Truth, quá trình tiêm lỗi, xác minh, cleanup và kết quả đánh giá có cấu trúc.
- **Audit Log** cung cấp dữ liệu truy vết các hành động nghiệp vụ quan trọng phục vụ giám sát và kiểm toán.

Domain Service chịu trách nhiệm thực hiện quy tắc nghiệp vụ và phối hợp các Repository trong phạm vi domain. Đây là lớp trung gian giữa API, Multi-Agent Core, lớp tích hợp và cơ sở dữ liệu; frontend và Agent không truy cập Repository trực tiếp.

**Lõi Multi-Agent (Multi-Agent Core).** Thành phần này sử dụng LangGraph và bốn Orchestrator chuyên trách để phối hợp bốn Agent. Planning Orchestrator điều phối việc tạo và lưu kế hoạch; Configuration Orchestrator điều phối quá trình sinh và kiểm tra CLI cho Operation WRITE; Execution Orchestrator kiểm tra dependency, Approval Gate và thực thi; Analysis Orchestrator tổng hợp evidence và quản lý kết luận phân tích. Ở tầng Agent, Planner Agent tạo kế hoạch nghiệp vụ, Configuration Agent chuyển yêu cầu WRITE thành CLI phù hợp, Network Agent thực thi Operation đã được kiểm soát và Analyst Agent tạo kết luận chẩn đoán. LangGraph quản lý thứ tự và nhánh xử lý của workflow, nhưng không thay thế Domain Service trong việc quản lý dữ liệu nghiệp vụ dài hạn.

**Lớp tích hợp (Integration Layer).** Lớp này cô lập hệ thống khỏi chi tiết của những công nghệ và dịch vụ bên ngoài:

- **LLM Integration** sử dụng LangChain và `ChatNVIDIA` để gửi prompt đến NVIDIA AI Endpoint, nhận phản hồi và chuyển kết quả cho Planner, Configuration hoặc Analyst Agent.
- **GNS3 Integration** sử dụng GNS3 Provider để kiểm tra khả năng truy cập GNS3 Server trước khi hệ thống lập kế hoạch hoặc phân tích tác vụ mạng.
- **Network Device Integration** cung cấp `NetworkTool` với backend Netmiko hoặc Nornir, chuẩn bị kết nối từ inventory và credential, thực thi lệnh qua SSH/Telnet và chuẩn hóa kết quả trả về. Thành phần này được Network Agent sử dụng trong workflow; Benchmark Run Service cũng sử dụng nó để kiểm tra baseline, tiêm lỗi, xác minh và cleanup.

**Lớp lưu trữ (Persistence Layer).** Repository và SQLAlchemy đảm nhiệm ánh xạ, truy vấn và cập nhật dữ liệu trong PostgreSQL. Cơ sở dữ liệu lưu người dùng, session, quyền truy cập, inventory, credential, conversation, task, operation, approval, execution, benchmark, evaluation và audit. PostgreSQL là nguồn dữ liệu chuẩn đối với trạng thái nghiệp vụ của hệ thống.

**Hạ tầng triển khai.** Docker Compose vận hành FastAPI API, Workflow Worker, PostgreSQL, dịch vụ migration và pgAdmin. Worker lấy job, retry và phục hồi job bị gián đoạn bằng trạng thái PostgreSQL, thay cho việc chạy workflow trong request HTTP. Frontend chạy riêng qua REST/SSE; NVIDIA AI Endpoint và GNS3 Server nằm ngoài ranh giới ứng dụng.

Mối quan hệ giữa các thành phần được thiết kế theo nguyên tắc giới hạn trách nhiệm. Planner Agent không nhận credential và không chạy CLI; Network Agent không dùng LLM để tự lựa chọn mục tiêu hoặc diễn giải kết quả; Analyst Agent không kết nối và không thay đổi cấu hình thiết bị. Các thao tác WRITE phải được kiểm soát bởi Execution Service và Approval Gate trước khi Network Agent thực thi. Sự phân tách này làm giảm phạm vi ảnh hưởng khi một thành phần tạo kết quả không hợp lệ và hỗ trợ kiểm tra toàn bộ quá trình xử lý.

### 3.4.3. Cơ chế trao đổi và quản lý dữ liệu

Frontend và backend trao đổi dữ liệu bằng REST API và SSE trên nền HTTP. Sau khi đăng nhập, frontend gửi access token trong các yêu cầu đến API, bao gồm yêu cầu mở SSE bằng `fetch` để sử dụng được Bearer token. Router sử dụng Identity Service để kiểm tra tính hợp lệ của access token, trạng thái session, trạng thái tài khoản và permission tương ứng với chức năng được yêu cầu. Chỉ khi các điều kiện này được thỏa mãn, yêu cầu mới được chuyển đến Domain Service. Giao diện nhận Task Activity theo sequence qua SSE, tải lại dữ liệu hội thoại chi tiết sau các sự kiện cần thiết và sử dụng polling làm cơ chế dự phòng khi stream lỗi liên tiếp. Phiên bản hiện tại không sử dụng WebSocket hoặc Message Queue.

Đối với yêu cầu xử lý bằng AI, Conversation Service lưu Conversation và Message, sau đó API enqueue Workflow Job trong PostgreSQL; Worker claim job và gọi LangGraph ngoài request HTTP. Node `plan` sử dụng Planning Orchestrator để lấy tối đa năm Message ngay trước yêu cầu hiện tại từ PostgreSQL, sắp xếp theo thời gian và chuyển chúng cùng yêu cầu mới, inventory công khai và topology context cho Planner Agent. Lịch sử gần chỉ dùng để phân giải các tham chiếu như “thiết bị đó” hoặc “tiếp tục bước trước”; message hiện tại vẫn là yêu cầu điều khiển chính. Structured output được kiểm tra bằng schema rồi lưu tạm trong LangGraph state dưới dạng `PlanningDraft`, chưa tạo Operation. Nếu kế hoạch chỉ có READ, Planning Orchestrator lưu kế hoạch và workflow đi thẳng đến `execute`. Nếu có WRITE, conditional edge chuyển state sang node `configure`; Configuration Orchestrator gọi Configuration Agent, chuẩn hóa CLI và đối chiếu interface với inventory GNS3. Kế hoạch hoàn chỉnh chỉ được chuyển thành Task Operation, Operation Dependency và Operation Device sau khi node phù hợp hoàn tất validation.

Trong quá trình thực thi, Execution Orchestrator đọc lại Task, Operation, dependency, mapping thiết bị và Approval từ Execution Service. Với Operation READ, Network Agent có thể gọi NetworkTool để thu thập trạng thái. Với Operation WRITE, workflow chỉ tiếp tục khi Approval Gate xác nhận nội dung đã được phê duyệt và vẫn khớp với command snapshot. NetworkTool lấy thông tin kết nối thông qua Inventory Service và Device Connection Provider, sau đó gửi lệnh đến thiết bị bằng SSH hoặc Telnet. Output của thiết bị được chuẩn hóa, lưu thành Execution và Device Action Log, rồi chuyển cho Analyst Agent làm bằng chứng phân tích.

Planner Agent, Configuration Agent và Analyst Agent trao đổi với NVIDIA AI Endpoint thông qua lớp tích hợp LLM; API key và cấu hình model được quản lý tại backend, không được gửi xuống frontend. Network Agent không gọi LLM. Analyst nhận output thực thi, thông tin thiết bị và evidence đã thu thập để tạo `AnalysisResult`. Khi evidence chưa đầy đủ, workflow có thể tạo các bước điều tra READ-only bổ sung trong giới hạn số vòng đã cấu hình; kết quả cuối cùng được lưu thành Message và dữ liệu đánh giá có cấu trúc.

GNS3 Provider giao tiếp với GNS3 Server qua HTTP/REST để kiểm tra khả năng truy cập môi trường. Topology và trạng thái các node được quản lý tại GNS3; phiên bản hiện tại chưa đồng bộ toàn bộ graph node–link vào cơ sở dữ liệu của hệ thống. Hoạt động CLI bên trong thiết bị được thực hiện qua NetworkTool dựa trên thông tin kết nối trong Inventory. Đối với benchmark, Benchmark Service đọc Scenario đã lưu, kiểm tra precondition, sử dụng NetworkTool để tiêm lỗi và xác minh trạng thái, tạo yêu cầu chẩn đoán qua workflow, lưu Evaluation, sau đó thực hiện cleanup và kiểm chứng trạng thái khôi phục.

PostgreSQL được sử dụng làm nguồn dữ liệu chuẩn đối với vòng đời Conversation, Task, Operation, Approval, Execution, Benchmark Run và Evaluation. Mọi thay đổi nghiệp vụ dài hạn được thực hiện thông qua Domain Service và Repository. Các cập nhật cần bảo đảm tính nhất quán, chẳng hạn xoay session hoặc xử lý phê duyệt hết hạn, sử dụng transaction và cơ chế khóa dữ liệu phù hợp tại tầng lưu trữ.

LangGraph state chỉ chứa dữ liệu chuyển tiếp cần thiết giữa các node trong một lượt xử lý, chẳng hạn Conversation, Message, `PlanningDraft`, Task, Execution Result, Analysis Result, vòng điều tra và mức độ bao phủ evidence. State này không được sử dụng như nguồn dữ liệu cạnh tranh với PostgreSQL. Trước mỗi giai đoạn quan trọng, Orchestrator đọc lại trạng thái nghiệp vụ đã lưu để hạn chế việc thực thi dựa trên dữ liệu cũ.

Khi một Task WRITE dừng để chờ phê duyệt, hệ thống lưu Task, Operation, Approval và command snapshot trong PostgreSQL rồi kết thúc lượt workflow hiện tại. Sau khi người dùng đưa ra quyết định, API enqueue job `APPROVAL`; Workflow Worker tải lại Task từ PostgreSQL và tiếp tục từ nhánh `approval → execute`, không lập kế hoạch hoặc sinh CLI lại. Nhờ đó, hệ thống không phải duy trì một tiến trình LangGraph hoặc kết nối HTTP liên tục trong toàn bộ thời gian chờ phê duyệt, đồng thời vẫn bảo đảm tính tuần tự, khả năng truy vết và tính nhất quán của nội dung đã được chấp thuận.

## 3.5. Thiết kế kiến trúc Multi-Agent

| Tác tử/thành phần      | Đầu vào                                                       | Chức năng                                                                         | Đầu ra và giới hạn                                              |
| ---------------------- | ------------------------------------------------------------- | --------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| Planner Agent          | Yêu cầu người dùng, inventory công khai, topology neighbor, diagnostic playbook và JSON Schema | Phân tích ý định; tạo Operation, device mapping, READ/WRITE, dependency và yêu cầu cấu hình | ExecutionPlanCreate; không sinh CLI WRITE, không kết nối thiết bị |
| Configuration Agent    | Kế hoạch, yêu cầu cấu hình, thiết bị và interface hợp lệ       | Chuyển yêu cầu của từng Operation WRITE thành CLI và chuẩn hóa lệnh                 | Kế hoạch có commands WRITE; không kết nối hoặc thực thi trên thiết bị |
| Network Agent          | Operation và danh sách command cho mapping                    | Kiểm tra input và gọi NetworkTool qua adapter                                     | NetworkExecutionResult; không dùng LLM, không tự chọn mạng đích |
| Analyst Agent          | Command outputs, hostname, trạng thái thực thi                | Tóm tắt phát hiện, giả thuyết, khuyến nghị; tạo kết luận RCA dạng JSON            | AnalysisResult; không kết nối hay sửa thiết bị                  |
| Planning Orchestrator  | Message, Conversation, inventory và topology                  | Tạo Task gốc, gọi Planner, kiểm tra device/interface, tạo PlanningDraft và lưu kế hoạch hoàn chỉnh | PlanningDraft hoặc Task/plan đã xác thực |
| Configuration Orchestrator | ExecutionPlanCreate, inventory và interface GNS3          | Xác định WRITE operation, gọi Configuration Agent, kiểm tra command/interface và ghi activity | Kế hoạch có CLI WRITE đã xác thực |
| Execution Orchestrator | Task và graph operation                                       | Kiểm tra dependency, Approval Gate, thực thi và cập nhật trạng thái               | Execution/result/action logs                                    |
| Analysis Orchestrator  | Task, kết quả thực thi, playbook, Evidence Coverage, inventory và topology | Chuẩn hóa evidence, áp dụng Causal Evidence Gate, điều phối vòng điều tra và tạo FINAL_RESPONSE | Message cuối cùng, structured diagnosis và dấu vết evidence |

### 3.5.1. Planner Agent

Planner Agent chịu trách nhiệm **phân tích ý định và đề xuất kế hoạch thực hiện ở mức nghiệp vụ**. Agent chuyển yêu cầu ngôn ngữ tự nhiên thành `ExecutionPlanCreate`, xác định Operation, thiết bị, chế độ READ/WRITE và dependency. Planner tạo lệnh cho bước READ thu thập dữ liệu; với bước WRITE, Planner chỉ mô tả `configuration_requirements` và không tự sinh CLI cấu hình.

Đầu vào của Planner gồm nội dung yêu cầu, danh sách thiết bị được phép sử dụng, thông tin inventory công khai, danh sách interface đã biết, quan hệ topology neighbor, diagnostic playbook phù hợp và JSON Schema của `ExecutionPlanCreate`. Thông tin inventory cung cấp `device_id`, hostname, brand, category, device type, location và interface cần thiết cho quá trình lập kế hoạch, nhưng không chứa username, password, secret hoặc khóa mã hóa credential. Planner chỉ được tham chiếu những thiết bị và interface có trong ngữ cảnh đầu vào, không được tự tạo thiết bị hoặc suy đoán cổng vật lý không tồn tại.

Đối với mỗi yêu cầu, Planner thực hiện các nhiệm vụ sau:

1. Xác định loại Task, chẳng hạn cấu hình, chẩn đoán hoặc tác vụ tổng hợp.
2. Phân rã mục tiêu thành danh sách Operation có thứ tự và `operation_intent` rõ ràng.
3. Tạo `operation_parameters`: Operation READ chứa `command` hoặc `commands`; Operation WRITE chứa `configuration_requirements` mô tả mục tiêu cấu hình.
4. Gán Operation cho thiết bị bằng `device_id`, xác định vai trò SOURCE, TARGET hoặc CONTEXT và lựa chọn `access_mode` READ/WRITE.
5. Thiết lập dependency giữa các Operation bằng `ON_SUCCESS` hoặc `ON_COMPLETION`, chỉ tham chiếu đến bước đứng trước để giữ kế hoạch ở dạng DAG.
6. Tách bước thu thập dữ liệu, thay đổi cấu hình và xác minh kết quả thành các Operation phù hợp.

Với yêu cầu cấu hình, Planner mô tả mục tiêu, tham số và ràng buộc của thay đổi trong `configuration_requirements`. Operation WRITE phải phụ thuộc vào các bước kiểm tra cần thiết và sau khi được Configuration Agent bổ sung CLI, kế hoạch phải vượt qua Approval Gate trước khi Network Agent thực thi.

Với yêu cầu chẩn đoán, Planner ưu tiên tạo các Operation READ nhằm thu thập evidence theo diagnostic playbook. Khi cần quan sát thiết bị lân cận, Agent sử dụng topology neighbor và ánh xạ interface đã được cung cấp, không tự suy đoán quan hệ mạng. Những Operation do vòng điều tra bổ sung tạo ra cũng bị giới hạn ở lệnh READ-only để tránh thay đổi cấu hình trong quá trình thu thập bằng chứng.

Kết quả từ LLM phải là một JSON object phù hợp với `ExecutionPlanCreate`. Planner kiểm tra dữ liệu bằng Pydantic. Nếu phản hồi sai JSON, Operation READ thiếu command, Operation WRITE thiếu yêu cầu cấu hình hoặc vi phạm schema, Agent gửi lại lỗi validation để mô hình sửa trong giới hạn retry và timeout. Planning Orchestrator tiếp tục kiểm tra device ID, thứ tự và dependency rồi tạo `PlanningDraft`. Conditional edge của LangGraph quyết định chuyển draft sang node `configure` khi có WRITE hoặc lưu kế hoạch READ để đi thẳng đến `execute`.

Planner Agent không lưu trực tiếp dữ liệu nghiệp vụ, không giải mã credential, không sinh CLI WRITE, không mở kết nối SSH/Telnet, không phê duyệt cấu hình và không thực thi command. Việc tách lập kế hoạch khỏi sinh cấu hình giúp thu hẹp trách nhiệm của Planner và cho phép kiểm tra riêng từng đầu ra.

### 3.5.2. Configuration Agent

Configuration Agent là tác tử chuyên trách **chuyển yêu cầu cấu hình ở mức nghiệp vụ thành câu lệnh CLI**. Agent được tách khỏi Planner Agent để việc phân rã mục tiêu và việc sinh cú pháp cấu hình có thể được kiểm tra độc lập. Đầu vào của Agent gồm `ExecutionPlanCreate` đã được Planner tạo, inventory công khai của thiết bị và danh sách interface hợp lệ theo từng `device_id`. Inventory chỉ chứa định danh, hostname, `device_type` và interface cần thiết; username, password, secret hoặc dữ liệu giải mã credential không được đưa vào prompt.

Agent chỉ xử lý những Operation có ít nhất một ánh xạ thiết bị mang `access_mode=WRITE`. Các Operation READ được giữ nguyên và không được gửi đến mô hình. Đối với mỗi Operation WRITE, Agent nhận `operation_order`, `operation_intent`, `configuration_requirements`, loại thiết bị và các interface được phép sử dụng. Từ ngữ cảnh này, Agent tạo danh sách command phù hợp với hệ điều hành hoặc driver của thiết bị, nhưng không được thay đổi loại Task, thêm hoặc xóa Operation, sửa dependency, đổi thiết bị hay thay đổi thứ tự kế hoạch.

Quy trình sinh cấu hình của Configuration Agent gồm các bước sau:

1. Duyệt kế hoạch và xác định tập `operation_order` của các Operation WRITE.
2. Tạo inventory tối thiểu gồm `id`, `hostname`, `device_type` và danh sách interface hợp lệ của các thiết bị liên quan.
3. Chỉ đưa các Operation WRITE cùng hợp đồng JSON đầu ra vào prompt dành cho Configuration Agent.
4. Gọi LLM trong giới hạn `timeout_seconds` và nhận structured output dạng `GeneratedConfigurationSet`.
5. Bóc JSON object từ phản hồi, xác thực bằng Pydantic và yêu cầu mô hình tạo lại khi dữ liệu sai cấu trúc trong giới hạn `max_validation_retries`.
6. Ghép command vào đúng Operation WRITE theo `operation_order`, loại `configuration_requirements` đã được biên dịch và trả về một bản kế hoạch mới.

Structured output phải chứa đúng một `GeneratedConfiguration` cho mỗi Operation WRITE. Hệ thống từ chối kết quả có `operation_order` trùng lặp, thiếu cấu hình cho một Operation hoặc chứa cấu hình ngoài tập Operation dự kiến. Mỗi phần tử phải có ít nhất một command. Cơ chế đối chiếu này ngăn mô hình ghép nhầm cấu hình vào Operation khác hoặc âm thầm bỏ sót một thay đổi đã được Planner yêu cầu.

Trước khi được đưa vào kế hoạch, command được chuẩn hóa bằng `normalize_config_commands`. Các lệnh quản lý phiên như `configure terminal`, `end`, `write memory` được loại bỏ vì việc vào chế độ cấu hình, lưu cấu hình và đóng phiên thuộc trách nhiệm của NetworkTool. Sau khi Agent trả kết quả, Configuration Orchestrator tiếp tục đối chiếu các interface xuất hiện trong CLI với inventory GNS3. Kế hoạch tham chiếu interface vật lý không tồn tại bị từ chối trước khi được lưu. Orchestrator đồng thời ghi các activity `CONFIGURATION_STARTED` và `CONFIGURATION_COMPLETED` để giao diện thể hiện đúng trình tự xử lý.

Kết quả cuối của node `configure` vẫn là `ExecutionPlanCreate`, trong đó Operation READ không thay đổi và Operation WRITE đã có trường `commands`. Workflow yêu cầu Planning Orchestrator lưu kế hoạch hoàn chỉnh thành các bản ghi nghiệp vụ trước khi chuyển sang `execute`. Execution Orchestrator tiếp tục kiểm tra dependency; Approval Gate tạo và kiểm tra command snapshot trước khi Network Agent được gọi.

Configuration Agent không kết nối GNS3 hoặc thiết bị mạng, không đọc credential, không quan sát output thực tế, không phê duyệt thay đổi và không tự khắc phục lỗi sau thực thi. Nếu mô hình không trả JSON hợp lệ sau số lần thử cho phép hoặc vượt quá timeout, giai đoạn lập kế hoạch kết thúc với lỗi có cấu trúc thay vì chuyển một cấu hình không xác định xuống thiết bị.

### 3.5.3. Network Agent

Network Agent là tác tử chuyên trách **thực thi câu lệnh trên thiết bị mạng**. Khác với Planner Agent, Configuration Agent và Analyst Agent, thành phần này không sử dụng LLM để suy luận, không tự lựa chọn thiết bị, không xây dựng kế hoạch và không sinh thêm câu lệnh. Đầu vào của Agent phải là Operation cùng `TaskOperationDevice` đã được các Orchestrator kiểm soát và lưu trong cơ sở dữ liệu. Cách thiết kế này làm cho hành vi thực thi có tính xác định: Agent chỉ gửi đúng những command đã có trong Operation đến đúng `device_id` và theo đúng `access_mode` được chỉ định.

Trước khi kết nối thiết bị, Network Agent kiểm tra `operation_id` trong ánh xạ thiết bị có trùng với Operation đang xử lý hay không. Agent tiếp tục trích xuất command từ `operation_parameters`; hệ thống hỗ trợ cả một lệnh trong trường `command` và nhiều lệnh trong trường `commands`, đồng thời loại bỏ chuỗi rỗng. Operation không chứa command hợp lệ bị từ chối trước khi gọi công cụ mạng. Những kiểm tra này ngăn việc dùng nhầm ánh xạ thiết bị hoặc chuyển một kế hoạch chưa hoàn chỉnh xuống tầng thực thi.

Quy trình thực thi của Network Agent gồm các bước chính sau:

1. Nhận Operation và ánh xạ `TaskOperationDevice` từ Execution Orchestrator.
2. Kiểm tra quan hệ giữa Operation và thiết bị, sau đó chuẩn hóa danh sách command đầu vào.
3. Gọi `NetworkTool.execute(device_id, access_mode, commands)` trong một thread riêng để thao tác mạng đồng bộ không chặn event loop của backend.
4. Nhận danh sách `CommandResult` từ NetworkTool và đóng gói thành `NetworkExecutionResult` có trạng thái `SUCCESS`.
5. Khi xảy ra lỗi kết nối, timeout, lỗi công cụ hoặc thiết bị từ chối câu lệnh, chuyển exception thành kết quả `FAILED` có `error_message` thay vì làm gián đoạn toàn bộ workflow.

`NetworkTool` là giao diện trừu tượng giúp Network Agent không phụ thuộc trực tiếp vào Netmiko hoặc Nornir. Với backend Netmiko, công cụ lấy thông tin kết nối và credential thông qua `NetworkService`, mở một phiên riêng cho mỗi lần thực thi và luôn đóng phiên trong khối `finally`. Nhờ đó, credential không đi qua prompt của LLM và một phiên lỗi không bị tái sử dụng cho lần thực thi sau.

Hai chế độ truy cập được xử lý khác nhau. Với `READ`, NetworkTool lần lượt sử dụng `send_command` cho từng câu lệnh và giữ lại output riêng của từng command để làm evidence cho Analyst Agent. Với `WRITE`, công cụ chuẩn hóa danh sách cấu hình rồi sử dụng `send_config_set` để đưa thiết bị vào chế độ cấu hình. Hệ thống kiểm tra output để phát hiện các thông báo CLI như `% Invalid input`, `% Incomplete command`, `% Ambiguous command`, `% Unknown command` hoặc `% Error`. Cấu hình chỉ được lưu bằng `save_config` khi toàn bộ quá trình không phát hiện lỗi. Tuy nhiên, Network Agent không tự quyết định một Operation WRITE có được chạy hay không; Execution Orchestrator và Approval Gate phải xác nhận trạng thái phê duyệt và command snapshot trước khi gọi Agent.

Kết quả của mỗi lần gọi được chuẩn hóa thành `NetworkExecutionResult`, gồm `operation_id`, `operation_device_id`, `device_id`, `access_mode`, trạng thái, danh sách `CommandResult` và thông báo lỗi nếu có. Bao quanh Network Agent, `MappingExecutor` chịu trách nhiệm cập nhật trạng thái mapping, tạo `TaskExecution`, đo `duration_ms`, lưu output, ghi `DeviceActionLog` theo từng command và phát activity `COMMAND_EXECUTED`. Vì vậy, Network Agent chỉ đảm nhiệm ranh giới thực thi kỹ thuật, còn vòng đời nghiệp vụ, audit và khả năng truy vết vẫn thuộc Execution Orchestrator cùng Execution Service.

Phạm vi trách nhiệm trên bảo đảm Network Agent không vượt quyền: Agent không truy cập Ground Truth của benchmark, không phân tích nguyên nhân sự cố, không thay đổi kế hoạch, không bỏ qua dependency và không tự phê duyệt cấu hình. Output của Agent được chuyển cho Analysis Orchestrator và Analyst Agent làm dữ liệu đầu vào cho bước phân tích tiếp theo.

### 3.5.4. Analyst Agent

Analyst Agent là tác tử chuyên trách **diễn giải kết quả thực thi và hình thành kết luận chẩn đoán có cấu trúc**. Agent không kết nối thiết bị và không tự chạy command; đầu vào của nó được Analysis Orchestrator xây dựng từ các `NetworkExecutionResult` đã lưu. Mỗi phần tử đầu vào gồm tên thiết bị dễ đọc, chế độ truy cập, trạng thái thực thi, command, output, lỗi kỹ thuật và `structured_evidence` được parser của backend trích xuất. Khi có thể truy cập GNS3, Orchestrator còn bổ sung thông tin topology lân cận; đối với tác vụ chẩn đoán, trạng thái Evidence Coverage của playbook cũng được đưa vào ngữ cảnh phân tích.

Analyst Agent sử dụng LLM để tổng hợp dữ liệu thành `AnalysisResult`. Kết quả gồm `summary`, `findings`, `likely_causes`, `recommendations`, `requires_more_data`, `confidence`, `evidence_gaps`, `suggested_checks`, `is_anomaly`, `root_causes`, `suspected_causes` và `execution_issues`. Trong đó, `root_causes` sử dụng cấu trúc `PredictedRootCause` để biểu diễn thiết bị, interface có thể rỗng và loại sự cố; `confidence` nằm trong khoảng từ 0 đến 1. Trường `suspected_causes` do Causal Evidence Gate của backend bổ sung sau hậu kiểm, còn `execution_issues` được backend tạo từ các lỗi kết nối hoặc thực thi xác định; hai trường này không phải kết luận tự do do LLM thiết lập. Các danh sách và độ dài chuỗi được giới hạn nhằm giảm nguy cơ phản hồi dài, lặp lại hoặc bị cắt giữa chừng.

Quy trình phân tích của Analyst Agent gồm các bước sau:

1. Nhận danh sách output thực thi đã được Analysis Orchestrator chuẩn hóa và gắn hostname.
2. Tạo prompt gồm execution outputs và JSON Schema của `AnalysisResult`; trường `suspected_causes` không được cho LLM tự thiết lập vì đây là kết quả hậu kiểm của backend.
3. Gọi LLM trong giới hạn `timeout_seconds` áp dụng cho toàn bộ chu kỳ phân tích và retry.
4. Bóc JSON object từ `content`; chỉ sử dụng `reasoning_content` khi nội dung chính thực sự rỗng.
5. Xác thực các trường bắt buộc và toàn bộ payload bằng Pydantic. Khi phản hồi không hợp lệ, gửi lại lỗi cùng giới hạn độ dài để mô hình tạo một JSON mới trong giới hạn `max_validation_retries`.
6. Trả `AnalysisResult` cho Analysis Orchestrator để tiếp tục kiểm tra evidence và quyết định điều tra bổ sung hoặc kết thúc workflow.

Cơ chế parser ưu tiên JSON nghiêm ngặt, đồng thời hỗ trợ sửa một số lỗi hình thức giới hạn thường gặp ở mô hình, chẳng hạn key thuộc schema bị thiếu dấu ngoặc kép hoặc dấu phẩy thừa trước dấu đóng. Việc sửa chỉ tác động đến cấu trúc JSON đã biết, không thay đổi nội dung command hoặc tự tạo thêm kết luận. Payload bắt buộc phải khai báo rõ `is_anomaly`, `root_causes`, `confidence`, `evidence_gaps` và `suggested_checks`; nếu thiếu các trường này, kết quả bị xem là không hợp lệ và được yêu cầu tạo lại.

Các kiểm tra bổ sung trong `suggested_checks` phải là READ-only. Schema chỉ chấp nhận command bắt đầu bằng `show`, `ping` hoặc `traceroute`, mỗi đề xuất phải chỉ rõ thiết bị và lý do, đồng thời số lượng command được giới hạn. Analysis Orchestrator ánh xạ hostname với inventory, loại lệnh đã thực thi và ưu tiên các command còn thiếu từ diagnostic playbook trước khi tạo Operation điều tra mới. Vì vậy, đề xuất của LLM không được chuyển thẳng thành thao tác cấu hình và không thể mở rộng quyền sang WRITE.

Kết luận của Analyst Agent chưa mặc nhiên được coi là nguyên nhân gốc đã xác nhận. Backend parse output thiết bị thành `DiagnosticEvidence`, tính mức độ bao phủ so với `required_evidence` của playbook và sử dụng Causal Evidence Gate để đối chiếu từng candidate với thiết bị, interface và phạm vi topology. Khi evidence đã đầy đủ nhưng Agent chưa tạo `root_causes`, hệ thống cho phép một lần diễn giải lại có kiểm soát. Khi evidence còn thiếu, workflow có thể tạo vòng điều tra READ-only bổ sung; khi đạt `AGENT_MAX_INVESTIGATION_ROUNDS`, hệ thống dừng an toàn và ghi lại lý do cùng evidence còn thiếu.

Nếu LLM timeout hoặc không tạo được `AnalysisResult` hợp lệ sau các lần retry, Analysis Orchestrator tạo phản hồi dự phòng từ trạng thái và số command đã thực thi để cuộc hội thoại không bị treo. Phản hồi này chỉ thông báo rằng dữ liệu chưa thể được chuẩn hóa, đặt `requires_more_data=true` và không tạo `root_causes`; do đó evaluator không xem đây là một kết luận RCA hợp lệ.

Sau khi hoàn tất Evidence Gate, Analysis Orchestrator định dạng kết quả thành phản hồi tiếng Việt dễ đọc, lưu Message loại `FINAL_RESPONSE` và ghi activity tương ứng. Analyst Agent không truy cập Ground Truth của benchmark, không dùng nhãn kỳ vọng để tạo dự đoán, không sửa Task hoặc kế hoạch, không phê duyệt và không thực thi lệnh. Sự phân tách này giúp kết quả benchmark phản ánh năng lực phân tích từ bằng chứng quan sát thay vì rò rỉ đáp án từ bộ đánh giá.

### 3.5.5. Orchestrator và cơ chế điều phối

Hệ thống sử dụng **cơ chế điều phối tập trung** nhằm bảo đảm các Agent chỉ thực hiện đúng nhiệm vụ chuyên môn và không trực tiếp quyết định toàn bộ vòng đời của một yêu cầu. Lớp điều phối gồm Planning Orchestrator, Configuration Orchestrator, Execution Orchestrator và Analysis Orchestrator. Các thành phần này không thay thế Agent trong việc suy luận hoặc thực thi kỹ thuật; chúng chịu trách nhiệm chuẩn bị ngữ cảnh, gọi đúng Agent, kiểm tra đầu ra, áp dụng quy tắc nghiệp vụ, lưu trạng thái và quyết định giai đoạn tiếp theo của workflow.

**Planning Orchestrator** quản lý node `plan`. Thành phần này tạo Task gốc từ Message của người dùng, ghi các activity ban đầu, lấy danh sách thiết bị khả dụng, topology và diagnostic playbook phù hợp, sau đó gọi Planner Agent. Kế hoạch trả về được kiểm tra định danh thiết bị, thứ tự Operation, quan hệ phụ thuộc và interface được tham chiếu. Kết quả của giai đoạn này là `PlanningDraft` gồm Task gốc, `ExecutionPlanCreate`, inventory công khai và ánh xạ interface. Planning Orchestrator chưa lưu Operation WRITE tại thời điểm này. Khi draft chỉ chứa READ, thành phần này lưu ngay kế hoạch hoàn chỉnh; khi có WRITE, conditional edge chuyển draft sang node `configure`. Nếu Planner hoặc bước validation phát sinh lỗi, Task được chuyển sang trạng thái thất bại và nguyên nhân được ghi vào timeline thay vì tiếp tục với kế hoạch chưa hợp lệ.

**Configuration Orchestrator** quản lý nghiệp vụ chính bên trong node LangGraph `configure`, qua đó cô lập quá trình chuyển yêu cầu WRITE thành CLI khỏi node `plan`. Thành phần này nhận `PlanningDraft`, đếm số Operation WRITE, ghi activity `CONFIGURATION_STARTED`, gọi Configuration Agent với kế hoạch, inventory công khai và danh sách interface hợp lệ, sau đó kiểm tra lại CLI được sinh. Các interface vật lý xuất hiện trong command phải tồn tại trong inventory GNS3; command phải được ánh xạ đúng Operation và đã loại các lệnh quản lý phiên không thuộc trách nhiệm của Agent. Chỉ khi toàn bộ kiểm tra thành công, Orchestrator mới ghi `CONFIGURATION_COMPLETED`. Workflow sau đó yêu cầu Planning Orchestrator lưu kế hoạch đã bổ sung CLI thành các bản ghi nghiệp vụ rồi mới chuyển sang node `execute`. Nếu cấu hình hoặc validation thất bại, Task được đánh dấu `FAILED` tại giai đoạn `CONFIGURATION`.

**Execution Orchestrator** quản lý việc thực thi DAG đã được lưu. Trước khi chạy, thành phần này đọc lại Task từ PostgreSQL để ngăn callback phê duyệt đến muộn làm sống lại một Task đã kết thúc. Các Operation được duyệt theo `display_order`; điều kiện dependency được đánh giá trước khi thực thi. Dependency `ON_SUCCESS` yêu cầu Operation trước thành công, trong khi `ON_COMPLETION` chỉ yêu cầu Operation trước đã kết thúc. Operation không thỏa mãn dependency được đánh dấu `SKIPPED`, không được gửi xuống thiết bị.

Đối với mỗi Operation đủ điều kiện, Execution Orchestrator tải các `TaskOperationDevice` và chuyển chúng qua Approval Gate. Mapping READ có thể được thực hiện ngay; mapping WRITE chỉ được phép chạy khi quyết định phê duyệt còn hiệu lực và command hiện tại khớp với snapshot đã được phê duyệt. Nếu còn mapping chờ quyết định, Operation chuyển sang `WAITING_APPROVAL`, activity `APPROVAL_REQUESTED` được ghi lại và lượt workflow hiện tại tạm dừng an toàn. Khi người dùng phê duyệt hoặc từ chối, backend tải lại Task từ cơ sở dữ liệu và khởi chạy nhánh tiếp tục tại giai đoạn `execute`, thay vì giữ một tiến trình LangGraph hoạt động trong toàn bộ thời gian chờ.

Sau khi vượt Approval Gate, Execution Orchestrator sử dụng `MappingExecutor` để gọi Network Agent cho từng ánh xạ thiết bị. `MappingExecutor` tạo `TaskExecution` ở trạng thái `RUNNING`, đo thời gian, lưu output, cập nhật trạng thái mapping và ghi `DeviceActionLog` theo từng command. Trạng thái Operation được tính lại từ toàn bộ mapping; trạng thái Task được tổng hợp từ các Operation thành `SUCCESS`, `PARTIAL_SUCCESS`, `FAILED` hoặc trạng thái kết thúc tương ứng. Nếu một exception ngoài dự kiến xuất hiện, Execution Orchestrator ghi lỗi, kết thúc Task có kiểm soát và không âm thầm tiếp tục các bước phụ thuộc.

Execution Orchestrator còn hỗ trợ các vòng điều tra bổ sung. Kế hoạch điều tra được nối vào Task hiện có nhưng chỉ chứa Operation READ. Thành phần này chỉ thực thi những Operation vừa được bổ sung, tránh chạy lại các Operation trước đó đã hoàn tất. Cơ chế này cho phép Analyst yêu cầu thêm evidence mà vẫn duy trì một lịch sử Task thống nhất và không làm mất dấu mối quan hệ giữa kết quả ban đầu với dữ liệu thu thập sau đó.

**Analysis Orchestrator** quản lý giai đoạn diễn giải kết quả và kiểm soát bằng chứng. Thành phần này chỉ bắt đầu phân tích khi Task không còn ở trạng thái đang chạy hoặc chờ phê duyệt. Output kỹ thuật được gắn hostname, parse thành `DiagnosticEvidence` và kết hợp với topology cùng Evidence Coverage trước khi chuyển cho Analyst Agent. Kết quả `AnalysisResult` sau đó được đưa qua Causal Evidence Gate để phân loại nguyên nhân thành đã xác nhận hoặc còn nghi ngờ. Nếu evidence bắt buộc còn thiếu, Analysis Orchestrator ưu tiên command từ diagnostic playbook, kết hợp các `suggested_checks` hợp lệ của Analyst và tạo kế hoạch điều tra READ-only.

Khi evidence đã đầy đủ nhưng Analyst chưa tạo được root cause mặc dù đã nhận diện bất thường, Analysis Orchestrator có thể yêu cầu diễn giải lại đúng một lần. Khi LLM timeout hoặc trả structured output không hợp lệ, thành phần này tạo phản hồi dự phòng để workflow không bị treo, nhưng không xem phản hồi đó là một kết luận RCA hợp lệ. Sau khi đủ bằng chứng hoặc đạt giới hạn số vòng điều tra, Orchestrator định dạng nội dung dễ đọc, lưu Message `FINAL_RESPONSE` và ghi activity liên kết Message với Task.

Kế hoạch nghiệp vụ được biểu diễn bằng bốn thành phần chính: `Task` mô tả yêu cầu tổng thể; `TaskOperation` mô tả từng bước; `OperationDependency` biểu diễn quan hệ DAG; và `TaskOperationDevice` ánh xạ bước xử lý với thiết bị cùng quyền READ hoặc WRITE. Planner chỉ được tham chiếu Operation đứng trước để hạn chế chu trình. Bên cạnh đó, Approval, TaskExecution, DeviceActionLog và TaskActivityEvent lưu quyết định của người dùng, kết quả kỹ thuật và dấu vết thực thi.

PostgreSQL là nguồn dữ liệu chuẩn đối với toàn bộ trạng thái nghiệp vụ. LangGraph state chỉ vận chuyển dữ liệu cần thiết giữa các node trong một lượt chạy, chẳng hạn `PlanningDraft`, Task hiện tại, execution results, analysis, số vòng điều tra và mức bao phủ evidence. Draft chỉ tồn tại trong giai đoạn `plan → configure`; trước node `execute`, kế hoạch hoàn chỉnh phải được lưu vào PostgreSQL. Trước các giai đoạn quan trọng, Orchestrator đọc lại trạng thái đã lưu thay vì chỉ tin vào state trong bộ nhớ. Cách tổ chức này hỗ trợ tiếp tục sau phê duyệt, tránh thực thi lặp, xử lý callback muộn và phục hồi luồng dựa trên dữ liệu đã tồn tại.

Mọi Orchestrator đều ghi `TaskActivityEvent` để frontend hiển thị tiến trình theo trình tự. Activity chỉ phản ánh sự kiện đã xảy ra hoặc trạng thái đang chờ; dữ liệu thực thi chi tiết vẫn được lưu trong các bảng nghiệp vụ tương ứng. Nhờ đó, cơ chế điều phối vừa hỗ trợ người dùng theo dõi tiến trình xử lý, vừa duy trì khả năng truy vết cần thiết cho Audit Log và Benchmark Evaluation.

Sự phân tách giữa bốn Orchestrator tạo ra các ranh giới kiểm soát rõ ràng: Planning Orchestrator không trực tiếp thực thi CLI; Configuration Orchestrator không kết nối thiết bị; Execution Orchestrator không tự phân tích nguyên nhân sự cố; Analysis Orchestrator không được tạo thao tác WRITE. Các Agent cũng không truy cập Repository trực tiếp. Mọi thay đổi trạng thái dài hạn đều đi qua Domain Service, nhờ đó quy tắc nghiệp vụ, phân quyền, phê duyệt và audit không phụ thuộc vào phản hồi không xác định của LLM.

### 3.5.6. Quy trình thực thi Multi-Agent trên LangGraph

Trong mã nguồn, LangGraph biên dịch một graph thống nhất phục vụ hai chế độ kích hoạt: xử lý Message mới và tiếp tục Task sau phê duyệt. State chứa `entry_mode` với giá trị `message` hoặc `approval`; conditional edge tại `START` dùng giá trị này để chọn điểm xử lý tiếp theo. Các điều kiện được đặt trên cạnh và không được biểu diễn thành node nghiệp vụ riêng.

Khi `entry_mode=message`, yêu cầu đi qua `check_gns3` và `plan`. Khi `entry_mode=approval`, backend đã tải Task được lưu theo mapping phê duyệt và graph đi trực tiếp đến `execute`, không chạy lại bước kiểm tra GNS3, lập kế hoạch hoặc sinh cấu hình. Sau `plan`, conditional edge chuyển kế hoạch có WRITE qua `configure`; kế hoạch chỉ có READ đi thẳng đến `execute`. Node `analyze` tiếp tục sử dụng conditional edge để chọn `investigate` hoặc `finalize`.

Theo ký hiệu lý thuyết đồ thị, workflow được mô tả bởi `G = (V, E)`, trong đó `V = {START, check_gns3, plan, configure, execute, analyze, investigate, finalize, END}`. `START` và `END` là các đỉnh đặc biệt của LangGraph; tập node nghiệp vụ thực sự là `{check_gns3, plan, configure, execute, analyze, investigate, finalize}`. Tập cạnh `E` gồm các chuyển tiếp trực tiếp và có điều kiện được thể hiện trên Hình 3.3.

Các giới hạn vận hành được ngoại hóa qua biến môi trường: retry và timeout của Planner/Analyst, số vòng điều tra, ngưỡng confidence và giới hạn token Analyst. Cách này cho phép hiệu chỉnh thực nghiệm mà không thay đổi mã nguồn; các giới hạn bảo đảm hợp đồng như command READ-only và kích thước schema vẫn được cố định trong code.

Một approval có thể làm quy trình tạm dừng trong khoảng thời gian dài. Để tránh thực thi lại các lệnh đã xong, chế độ `approval` sử dụng Task và mapping đã lưu rồi đi từ `START` đến `execute`. Phần chờ quyết định của con người được ghi thành activity timeline và được loại trừ khỏi cách đo thời gian workflow AI. Cả hai chế độ gọi cùng `_graph`; việc chọn cạnh khởi đầu không làm thay đổi trạng thái nghiệp vụ đã lưu trong PostgreSQL.

```mermaid
flowchart TD
    START([START]) -->|entry_mode = message| CHECK[check_gns3]
    START -->|entry_mode = approval| EXEC[execute]
    CHECK --> PLAN[plan]
    PLAN -->|Có Operation WRITE| CONFIGURE[configure]
    PLAN -->|Chỉ có Operation READ| EXEC
    CONFIGURE --> EXEC
    EXEC --> ANALYZE[analyze]
    ANALYZE -->|Thiếu bằng chứng| INVESTIGATE[investigate / READ-only]
    INVESTIGATE --> ANALYZE
    ANALYZE -->|Đủ bằng chứng hoặc đạt giới hạn| FINAL[finalize]
    FINAL --> END([END])
```

_Hình 3.3. Đồ thị workflow thống nhất với conditional edge tại START._

| Node LangGraph | Thành phần xử lý chính | Kết quả |
| --- | --- | --- |
| `check_gns3` | GNS3 Provider | Xác nhận GNS3 Server có thể truy cập |
| `plan` | Planning Orchestrator và Planner Agent | `PlanningDraft`; kế hoạch READ đã lưu hoặc kế hoạch WRITE chờ cấu hình |
| `configure` | Configuration Orchestrator và Configuration Agent | Kế hoạch WRITE có CLI đã xác thực và được lưu |
| `execute` | Execution Orchestrator, Approval Gate và Network Agent | Kết quả thực thi hoặc trạng thái chờ phê duyệt |
| `analyze` | Analysis Orchestrator, Analyst Agent và Causal Evidence Gate | `AnalysisResult` cùng Evidence Coverage |
| `investigate` | Analysis Orchestrator và Execution Orchestrator | Operation READ bổ sung và evidence mới |
| `finalize` | Analysis Orchestrator | Message `FINAL_RESPONSE` hoặc phản hồi chờ phê duyệt |

## 3.6. Thiết kế các quy trình xử lý nghiệp vụ

Các sơ đồ hoạt động trong các mục 3.6.2–3.6.6 sử dụng hình chữ nhật để biểu diễn thao tác theo cấu trúc **thành phần thực hiện – động từ – đối tượng được tác động**; hình thoi biểu diễn câu hỏi điều kiện với hai nhánh **Có/Không**. Các thao tác lưu trữ được ghi rõ theo chức năng tạo mới, cập nhật hoặc ghi nhật ký. Ký hiệu bắt đầu/kết thúc chỉ giới hạn quy trình con tương ứng, không nhất thiết là trạng thái kết thúc của toàn bộ Task hoặc toàn bộ LangGraph.

### 3.6.1. Quy trình tiếp nhận và phân tích yêu cầu

Quy trình bắt đầu khi người dùng đã được xác thực gửi yêu cầu ngôn ngữ tự nhiên từ giao diện Chat. API kiểm tra quyền truy cập thông qua Identity Service và chuyển yêu cầu đến Conversation Service. Đối với hội thoại mới, Conversation Service tạo `Conversation` và lưu `Message` loại `USER_REQUEST`; đối với hội thoại đã tồn tại, Service kiểm tra hội thoại và lưu Message mới. Dữ liệu được ghi vào PostgreSQL trước khi khởi động xử lý AI nhằm duy trì lịch sử yêu cầu và bảo đảm Task được liên kết với `source_message_id` hợp lệ.

Sau khi lưu Message, API sử dụng Workflow Job Service để tạo `Workflow Job` loại `MESSAGE` trong PostgreSQL, rồi trả thông tin Conversation/Message cho frontend. **Workflow Worker** hoạt động độc lập với tiến trình API, nhận job từ PostgreSQL, tải lại Conversation và Message, sau đó gọi LangGraph để xử lý yêu cầu. Chỉ Message do người dùng gửi mới tạo job xử lý AI; Message do Agent hoặc System tạo ra chỉ được lưu trong lịch sử hội thoại. Đối với hội thoại mới, Worker còn có thể tạo tiêu đề sau khi xử lý workflow. Cơ chế này không sử dụng `BackgroundTasks` để chạy LangGraph trong tiến trình HTTP.

Trong lượt xử lý Message mới, LangGraph kiểm tra khả năng truy cập GNS3 trước khi chuyển đến giai đoạn lập kế hoạch. Planning Orchestrator tạo Task, ghi các Activity Event `MESSAGE_RECEIVED`, `TASK_CREATED`, lấy ngữ cảnh inventory/topology và gọi Planner Agent sinh kế hoạch. Task và Task Activity được lưu thông qua Domain Service và Repository. Nếu Planner hoặc bước lưu kế hoạch phát sinh lỗi sau khi Task đã được tạo, hệ thống cập nhật Task và ghi Activity Event lỗi tương ứng. Các bước cấu hình, thực thi, phân tích và phê duyệt được trình bày riêng từ mục 3.6.2 đến 3.6.6.

Song song với quá trình xử lý của Worker, frontend mở kết nối SSE theo `source_message_id`. API tìm Task liên kết với Message, đọc lại các Task Activity có sequence lớn hơn cursor và tiếp tục phát các sự kiện mới. Việc kết nối lại được hỗ trợ qua `Last-Event-ID` hoặc `after_sequence`; frontend có thể tải lại thông tin hội thoại và chuyển sang polling khi stream gặp lỗi liên tiếp. SSE phục vụ cập nhật tiến trình, trong khi PostgreSQL vẫn là nguồn dữ liệu chuẩn. Hình 3.4 chỉ minh họa sự tương tác tổng quát giữa các thành phần chính; chi tiết từng Operation và nhánh xử lý không được lặp lại trong sơ đồ này.

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant FE as Frontend
    participant API as FastAPI
    participant DS as Domain Services
    participant DB as PostgreSQL
    participant Worker as Workflow Worker
    participant Graph as LangGraph

    User->>FE: Gửi yêu cầu ngôn ngữ tự nhiên
    FE->>API: Gửi Message kèm access token
    API->>DS: Kiểm tra quyền và lưu yêu cầu
    DS->>DB: Tạo Conversation nếu cần và lưu USER_REQUEST
    DB-->>DS: Trả Conversation và Message
    DS-->>API: Trả Message đã lưu
    API->>DS: Yêu cầu tạo Workflow Job MESSAGE
    DS->>DB: Lưu Workflow Job
    API-->>FE: Trả Conversation và Message ID

    par Worker xử lý yêu cầu bất đồng bộ
        Worker->>DS: Yêu cầu nhận Workflow Job
        DS->>DB: Claim Workflow Job
        DS-->>Worker: Trả Job và thông tin tham chiếu
        Worker->>Graph: Chạy workflow cho Message
        Graph->>Graph: Kiểm tra GNS3 và điều phối lập kế hoạch
        Graph->>DS: Tạo Task và ghi Task Activity qua Orchestrator
        DS->>DB: Lưu Task và Task Activity
        Graph-->>Worker: Trả kết quả workflow
        Worker->>DS: Cập nhật trạng thái Workflow Job
        DS->>DB: Lưu trạng thái Job
    and Frontend nhận tiến trình qua SSE
        FE->>API: Mở SSE theo source_message_id
        loop Khi kết nối SSE hoạt động
            API->>DS: Đọc Task Activity sau sequence hiện tại
            DS->>DB: Truy vấn Task Activity
            DS-->>API: Trả các sự kiện đã lưu
            API-->>FE: Phát SSE task_activity
        end
    end
    FE-->>User: Hiển thị tiến trình và phản hồi
```

_Hình 3.4. Sơ đồ tuần tự tổng quát tiếp nhận yêu cầu và cập nhật tiến trình xử lý._

### 3.6.2. Quy trình lập kế hoạch và cấu hình mạng

Quy trình bắt đầu khi node `plan` nhận `Conversation` và `Message` của người dùng từ workflow state. Planning Orchestrator trước hết kiểm tra message có do người dùng gửi và có thuộc đúng cuộc hội thoại hay không. Sau đó, hệ thống tạo một bản ghi trong bảng `tasks`, liên kết bản ghi này với `conversation_id`, `source_message_id` và `user_id`. Task được tạo trước khi gọi mô hình ngôn ngữ nhằm bảo đảm mọi yêu cầu đều có dấu vết nghiệp vụ, kể cả khi Planner Agent timeout hoặc trả kết quả không hợp lệ. Hai activity `MESSAGE_RECEIVED` và `TASK_CREATED` cũng được ghi vào `task_activity_events` để frontend hiển thị tiến trình và hệ thống có thể kiểm toán quá trình xử lý.

Planning Orchestrator tiếp tục lấy danh sách thiết bị khả dụng từ Inventory Service, danh sách interface và quan hệ topology từ GNS3 Provider, cùng tối đa năm message trước đó trong cùng conversation. Các dữ liệu này chỉ được dùng làm ngữ cảnh đầu vào cho Planner Agent, không tạo thêm bản sao inventory hoặc topology trong domain Execution. Planner Agent nhận yêu cầu, inventory công khai, topology, lịch sử hội thoại, diagnostic playbook phù hợp và JSON Schema của `ExecutionPlanCreate`. Agent xác định `task_type`, phân rã mục tiêu thành các Operation, gán thiết bị, chỉ định `access_mode` và thiết lập dependency. Operation READ phải chứa `command` hoặc `commands`; Operation WRITE chỉ mô tả mục tiêu và ràng buộc trong `configuration_requirements`. Planner Agent không nhận credential và không trực tiếp sinh CLI WRITE.

Kết quả Planner trả về được kiểm tra theo structured schema, thứ tự Operation, dependency, `device_id` và tên interface. Sau khi Planner Agent sinh kế hoạch có cấu trúc, Planning Orchestrator ghi activity `PLAN_GENERATED` kèm số lượng Operation, rồi tiếp tục kiểm tra `device_id` và tên interface. Nếu kiểm tra sau đó thất bại, Task được đánh dấu `FAILED`; sự kiện `PLAN_GENERATED` chỉ phản ánh việc sinh kế hoạch, không chứng nhận toàn bộ kế hoạch đã hợp lệ. Tại thời điểm này hệ thống chưa tạo bản ghi Operation. Kế hoạch cùng Task, inventory và ánh xạ interface chỉ được đóng gói thành `PlanningDraft` trong workflow state. `PlanningDraft` là dữ liệu chuyển tiếp trong bộ nhớ giữa các node LangGraph, không phải bảng và không được lưu xuống PostgreSQL. Cách tổ chức này ngăn việc lưu một Operation WRITE chưa có CLI hoàn chỉnh.

Conditional edge sau node `plan` kiểm tra thuộc tính `requires_configuration` của `PlanningDraft`. Nếu toàn bộ ánh xạ thiết bị đều có quyền READ, workflow không đi qua Configuration Agent mà gọi ngay `persist_plan`. Tên gọi “lưu kế hoạch READ” ở đây không chỉ có nghĩa là lưu Task. Trong một lần vật hóa kế hoạch, hệ thống thực hiện các thay đổi sau:

- Cập nhật bản ghi `tasks` với `task_type`, trạng thái lập kế hoạch và thời điểm bắt đầu phù hợp.
- Tạo một bản ghi `task_operations` cho mỗi Operation, bao gồm intent, tham số lệnh, thứ tự hiển thị, mức rủi ro và trạng thái ban đầu.
- Tạo các bản ghi `operation_dependencies` biểu diễn quan hệ phụ thuộc giữa những Operation theo `ON_SUCCESS` hoặc `ON_COMPLETION`.
- Tạo các bản ghi `task_operation_devices` ánh xạ từng Operation tới thiết bị, `access_mode` READ và trạng thái thực thi ban đầu.
- Ghi ba activity `OPERATIONS_CREATED`, `DEPENDENCIES_CREATED` và `DEVICES_ASSIGNED` vào `task_activity_events`, kèm số lượng bản ghi logic tương ứng.

Các bản ghi `task_executions`, `device_action_logs` và `operation_device_approvals` chưa được tạo trong giai đoạn này. Chúng chỉ phát sinh ở node `execute`: `task_executions` và `device_action_logs` được tạo khi thực sự gửi lệnh đến thiết bị, còn approval chỉ được tạo cho ánh xạ WRITE cần người dùng phê duyệt.

Nếu kế hoạch có ít nhất một ánh xạ WRITE, node `plan` chưa gọi `persist_plan` mà chuyển `PlanningDraft` sang node `configure`. Configuration Orchestrator ghi activity `CONFIGURATION_STARTED` với trạng thái `RUNNING`, sau đó gọi Configuration Agent với kế hoạch WRITE, danh sách thiết bị cần thiết và ánh xạ interface. Configuration Agent phải trả đúng một cấu hình cho mỗi Operation WRITE theo `operation_order`; kết quả trùng, thiếu hoặc thừa Operation đều bị từ chối. Các lệnh quản lý phiên như `configure terminal`, `end` và `write memory` được loại khỏi payload vì NetworkTool chịu trách nhiệm quản lý chế độ cấu hình và lưu cấu hình.

Sau khi Configuration Agent trả kết quả, Configuration Orchestrator đối chiếu lại interface xuất hiện trong CLI với dữ liệu GNS3. Nếu hợp lệ, activity `CONFIGURATION_COMPLETED` được lưu và CLI được hợp nhất vào bản `ExecutionPlanCreate`. Planning Orchestrator sau đó mới gọi `persist_plan`; quá trình này cập nhật `tasks`, tạo `task_operations`, `operation_dependencies`, `task_operation_devices` và ghi các activity tạo kế hoạch giống nhánh READ. Điểm khác biệt là các Operation WRITE lúc này đã chứa danh sách lệnh CLI hoàn chỉnh, còn `task_operation_devices` mang `access_mode` WRITE để node `execute` áp dụng Approval Gate.

Nếu Planner Agent timeout, trả JSON sai schema, tham chiếu thiết bị hoặc interface không tồn tại, Task được cập nhật sang `FAILED` và activity `TASK_FAILED` được ghi với stage `PLANNING`. Nếu lỗi xảy ra trong quá trình sinh hoặc kiểm tra cấu hình, Task cũng được chuyển sang `FAILED`, nhưng activity lưu stage `CONFIGURATION`. Trong cả hai trường hợp, các Operation chưa được vật hóa, approval chưa được tạo và không có lệnh nào được gửi đến thiết bị. Nếu lỗi xảy ra khi ghi kế hoạch, stage được lưu là `PLAN_PERSISTENCE`, giúp phân biệt lỗi dữ liệu với lỗi của Planner hoặc Configuration Agent.

```mermaid
flowchart TD
    S([Bắt đầu]) --> A["Planning Orchestrator kiểm tra Conversation và Message"]
    A --> D1{"Conversation và Message hợp lệ?"}
    D1 -->|Không| A0["Planning Orchestrator từ chối yêu cầu không hợp lệ"]
    A0 --> E([Kết thúc])
    D1 -->|Có| B["Execution Service tạo Task PENDING"]
    B --> C["Planning Orchestrator ghi MESSAGE_RECEIVED và TASK_CREATED"]
    C --> D["Planning Orchestrator lấy Inventory, topology và lịch sử hội thoại"]
    D --> F["Planner Agent sinh ExecutionPlanCreate"]
    F --> G["Planning Orchestrator ghi PLAN_GENERATED"]
    G --> G1["Planning Orchestrator kiểm tra device ID và interface"]
    G1 --> D2{"Kế hoạch hợp lệ?"}
    D2 -->|Không| H["Planning Orchestrator cập nhật Task FAILED tại PLANNING"]
    H --> H1["Planning Orchestrator ghi TASK_FAILED tại PLANNING"]
    H1 --> E
    D2 -->|Có| I["Planning Orchestrator tạo PlanningDraft trong LangGraph State"]
    I --> D3{"Kế hoạch có Mapping WRITE?"}
    D3 -->|Không| M["Execution Service cập nhật Task theo ExecutionPlan"]
    D3 -->|Có| J["Configuration Orchestrator ghi CONFIGURATION_STARTED"]
    J --> K["Configuration Agent sinh CLI cho Operation WRITE"]
    K --> L["Configuration Orchestrator kiểm tra CLI và interface hợp lệ"]
    L --> D4{"CLI hợp lệ?"}
    D4 -->|Không| N["Planning Orchestrator cập nhật Task FAILED tại CONFIGURATION"]
    N --> N1["Planning Orchestrator ghi TASK_FAILED tại CONFIGURATION"]
    N1 --> E
    D4 -->|Có| O["Configuration Orchestrator ghi CONFIGURATION_COMPLETED"]
    O --> M
    M --> M1["Execution Service lưu Operation, Dependency và Device Mapping"]
    M1 --> D5{"Lưu kế hoạch thành công?"}
    D5 -->|Không| P["Planning Orchestrator cập nhật Task FAILED tại PLAN_PERSISTENCE"]
    P --> P1["Planning Orchestrator ghi TASK_FAILED tại PLAN_PERSISTENCE"]
    P1 --> E
    D5 -->|Có| Q["Planning Orchestrator ghi OPERATIONS_CREATED, DEPENDENCIES_CREATED, DEVICES_ASSIGNED"]
    Q --> R["LangGraph chuyển Task sang node execute"]
    R --> E
```

_Hình 3.5. Sơ đồ hoạt động lập kế hoạch và sinh cấu hình có điều kiện._

### 3.6.3. Quy trình thực thi DAG và tổng hợp trạng thái

Node `execute` tải Task đã lưu và chuyển nó sang `RUNNING`. Execution Orchestrator duyệt các Operation theo `display_order`, nhưng chỉ thực thi Operation khi dependency đã thỏa mãn. Với dependency `ON_SUCCESS`, Operation tiền nhiệm phải có trạng thái `SUCCESS`; với `ON_COMPLETION`, Operation tiền nhiệm chỉ cần thuộc một trạng thái kết thúc. Operation không thỏa điều kiện được đánh dấu `SKIPPED`. Cơ chế này cho phép biểu diễn DAG trong cơ sở dữ liệu nhưng thực thi theo một thứ tự xác định và có thể truy vết.

Mỗi Operation được ánh xạ đến một hoặc nhiều `TaskOperationDevice`. Approval Gate lọc các mapping được phép thực thi: mapping READ có thể chuyển trực tiếp đến Network Agent, trong khi mapping WRITE phải có approval hợp lệ. Mapping đã `SUCCESS`, `REJECTED` hoặc `SKIPPED` không được chạy lại. Điều này đặc biệt quan trọng khi workflow được tiếp tục sau phê duyệt hoặc khi callback đến muộn.

Với mỗi mapping đủ điều kiện, `MappingExecutor` tạo `TaskExecution` ở trạng thái `RUNNING`, gọi Network Agent, đo `duration_ms`, lưu output và cập nhật trạng thái mapping. Từng `CommandResult` được ghi thành `DeviceActionLog`; activity `COMMAND_EXECUTED` liên kết Task, Operation, mapping và execution tương ứng. Lỗi kết nối, timeout, lỗi công cụ hoặc lỗi CLI được chuyển thành kết quả `FAILED` có thông báo thay vì làm mất dấu lần thực thi.

Sau khi các mapping kết thúc, trạng thái Operation được tổng hợp theo quy tắc: toàn bộ mapping thành công tạo `SUCCESS`; có cả thành công và thất bại tạo `PARTIAL_SUCCESS`; toàn bộ bị từ chối tạo `REJECTED`; còn lại là `FAILED`. Tương tự, trạng thái Task được tổng hợp từ các Operation thành `SUCCESS`, `PARTIAL_SUCCESS`, `REJECTED` hoặc `FAILED`. Nếu Operation chuyển sang `WAITING_APPROVAL`, lượt workflow hiện tại tạm dừng và không thực thi các Operation phụ thuộc phía sau.

Execution Orchestrator luôn đọc lại trạng thái Task trước các bước quan trọng. Task đã kết thúc không bị khởi động lại bởi callback phê duyệt đến muộn; Operation đã hoàn tất không được thực thi lại khi resume. Đối với vòng điều tra bổ sung, Orchestrator chỉ chạy các Operation READ mới được nối vào Task, giữ nguyên kết quả của kế hoạch ban đầu.

```mermaid
flowchart TD
    S([Bắt đầu]) --> A["Execution Orchestrator đọc trạng thái Task"]
    A --> D1{"Task đã kết thúc?"}
    D1 -->|Có| B["Execution Orchestrator bỏ qua Task đã kết thúc"]
    B --> E([Kết thúc])
    D1 -->|Không| C["Execution Orchestrator cập nhật Task RUNNING và ghi EXECUTION_STARTED"]
    C --> D2{"Còn Operation cần xử lý?"}
    D2 -->|Không| T["Execution Orchestrator cập nhật trạng thái kết thúc của Task"]
    T --> T1["Execution Orchestrator ghi TASK_COMPLETED hoặc TASK_FAILED"]
    T1 --> U["LangGraph chuyển kết quả sang node analyze"]
    U --> E
    D2 -->|Có| F["Execution Orchestrator lấy Operation theo display_order"]
    F --> D3{"Operation đã kết thúc?"}
    D3 -->|Có| D2
    D3 -->|Không| D4{"Dependency đã thỏa mãn?"}
    D4 -->|Không| G["Execution Orchestrator cập nhật Operation và Device Mapping SKIPPED"]
    G --> D2
    D4 -->|Có| H["Execution Orchestrator lấy các Device Mapping"]
    H --> I["Execution Orchestrator chuyển Mapping tiếp theo đến Approval Gate"]
    I --> D5{"Mapping đủ điều kiện thực thi?"}
    D5 -->|Có| J["MappingExecutor cập nhật Mapping RUNNING"]
    J --> J1["MappingExecutor tạo TaskExecution RUNNING"]
    J1 --> K["Network Agent thực thi lệnh bằng NetworkTool"]
    K --> L["MappingExecutor cập nhật Mapping và TaskExecution với kết quả, thời gian, output"]
    L --> M["MappingExecutor lưu DeviceActionLog"]
    M --> M1["MappingExecutor ghi COMMAND_EXECUTED"]
    M1 --> D6{"Còn Mapping cần kiểm tra?"}
    D5 -->|Không| N["Approval Gate xử lý Mapping chưa đủ điều kiện thực thi"]
    N --> D6
    D6 -->|Có| I
    D6 -->|Không| O["Execution Orchestrator tổng hợp và cập nhật trạng thái Operation"]
    O --> D7{"Operation đang WAITING_APPROVAL?"}
    D7 -->|Có| P["Execution Orchestrator ghi APPROVAL_REQUESTED"]
    P --> P1["Execution Orchestrator cập nhật Task RUNNING để chờ Approval"]
    P1 --> U
    D7 -->|Không| D2
```

_Hình 3.6. Sơ đồ hoạt động thực thi DAG và tổng hợp trạng thái Task._

### 3.6.4. Quy trình chẩn đoán sự cố và phân tích nguyên nhân gốc

Với Task `DIAGNOSIS` hoặc `COMPOSITE`, Planner ưu tiên tạo Operation READ theo diagnostic playbook nhằm thu thập trạng thái interface, cấu hình đang chạy, route, neighbor hoặc dữ liệu giao thức liên quan. Kết quả từ Network Agent được Analysis Orchestrator gắn hostname, phân tích thành `DiagnosticEvidence` và kết hợp với topology GNS3. Evidence Coverage được tính bằng cách so sánh những loại evidence thực tế với `required_evidence` của các playbook đang áp dụng.

Analyst Agent nhận output đã chuẩn hóa, structured evidence và trạng thái coverage để tạo `AnalysisResult`. Kết quả bao gồm phát hiện, nguyên nhân có khả năng, mức tin cậy, khoảng trống evidence, các phép kiểm tra đề xuất và submission RCA có cấu trúc. Ground Truth của Benchmark Scenario không được đưa vào prompt của Planner hoặc Analyst.

Các ứng viên nguyên nhân đủ điều kiện được Analysis Orchestrator chuyển qua Causal Evidence Gate. Gate đối chiếu candidate root cause với bằng chứng trực tiếp, thiết bị, interface và phạm vi topology; nếu không có ứng viên hợp lệ thì bước hậu kiểm này không phát sinh. Candidate đủ bằng chứng được đưa vào `root_causes`; candidate chưa đủ bằng chứng được chuyển sang `suspected_causes`, đồng thời lý do bị hạ mức được bổ sung vào `evidence_gaps`. Khi playbook đã đủ evidence nhưng Analyst không tạo root cause dù đã phát hiện bất thường, hệ thống cho phép một lần diễn giải lại có kiểm soát trước khi kết luận.

Nếu evidence bắt buộc còn thiếu hoặc Analyst yêu cầu thêm dữ liệu, conditional edge sau node `analyze` có thể chuyển sang `investigate`. Analysis Orchestrator ưu tiên command còn thiếu từ playbook, kết hợp `suggested_checks` hợp lệ và ánh xạ chúng đến thiết bị mục tiêu hoặc láng giềng trong topology. Mọi Operation điều tra đều là READ-only; schema chỉ chấp nhận lệnh bắt đầu bằng `show`, `ping` hoặc `traceroute`. Các lệnh đã chạy được loại bỏ để tránh thu thập lặp lại không cần thiết.

Node `investigate` tạo thêm các Operation READ và Device Mapping thuộc Task trong PostgreSQL, thực thi các lệnh điều tra bổ sung, ghi TaskExecution/DeviceActionLog và quay lại `analyze`. Vòng lặp dừng khi evidence hoàn chỉnh, root cause đã được xác nhận, không còn phép kiểm tra mới hoặc đạt `AGENT_MAX_INVESTIGATION_ROUNDS`. Khi dừng, hệ thống ghi Evidence Coverage, evidence còn thiếu và lý do dừng vào activity. Nếu LLM timeout hoặc structured output không hợp lệ sau retry, Analysis Orchestrator tạo phản hồi dự phòng, không tạo root cause giả và đánh dấu cần thêm dữ liệu.

```mermaid
flowchart TD
    S([Bắt đầu]) --> A["Analysis Orchestrator đọc trạng thái Task"]
    A --> A1["Analysis Orchestrator tính Evidence Coverage từ Execution Results"]
    A1 --> D1{"Task đang RUNNING?"}
    D1 -->|Có| B["Analysis Orchestrator trả kết quả rỗng để chờ Approval"]
    B --> E([Kết thúc])
    D1 -->|Không| F["Analysis Orchestrator ghi ANALYSIS_STARTED"]
    F --> D2{"Task đã bị REJECTED?"}
    D2 -->|Có| C["Analysis Orchestrator tạo kết luận từ chối"]
    C --> C1["Analysis Orchestrator ghi ANALYSIS_COMPLETED"]
    C1 --> Z["LangGraph chuyển AnalysisResult sang node finalize"]
    Z --> E
    D2 -->|Không| G["Analyst Agent phân tích Execution Results và Diagnostic Evidence"]
    G --> D3{"Có ứng viên nguyên nhân cần hậu kiểm?"}
    D3 -->|Có| H["Causal Evidence Gate đối chiếu nguyên nhân với bằng chứng và topology"]
    H --> I["Analysis Orchestrator cập nhật root_causes, suspected_causes và evidence_gaps"]
    D3 -->|Không| J["Analysis Orchestrator tổng hợp AnalysisResult và lỗi thực thi"]
    I --> J
    J --> K["Analysis Orchestrator ghi ANALYSIS_COMPLETED và diagnosis_submission"]
    K --> D4{"Cần điều tra thêm và còn lượt hợp lệ?"}
    D4 -->|Không| Z
    D4 -->|Có| L["Analysis Orchestrator tạo kế hoạch điều tra READ-only"]
    L --> D5{"Có Operation READ bổ sung?"}
    D5 -->|Không| M["LangGraph cập nhật evidence_stop_reason NO_ADDITIONAL_CHECKS"]
    M --> A
    D5 -->|Có| N["Execution Service cập nhật Task cho lượt điều tra"]
    N --> N1["Execution Service lưu Operation, Dependency và Device Mapping điều tra"]
    N1 --> O["Execution Orchestrator ghi EXECUTION_STARTED cho lượt điều tra"]
    O --> P["Network Agent thực thi Operation READ bổ sung"]
    P --> P1["MappingExecutor lưu TaskExecution và DeviceActionLog điều tra"]
    P1 --> Q["LangGraph cộng dồn Execution Results"]
    Q --> Q1["LangGraph cập nhật investigation_round"]
    Q1 --> A
```

_Hình 3.7. Sơ đồ hoạt động chẩn đoán và thu thập bằng chứng bổ sung._

### 3.6.5. Quy trình phê duyệt và kiểm soát thực thi

Approval Gate phân biệt mapping READ và WRITE. Khi gặp một mapping WRITE chưa có approval, Execution Service tạo yêu cầu phê duyệt gồm danh sách command snapshot, SHA-256 request hash, thời điểm tạo và thời hạn hiệu lực; mapping chuyển sang `WAITING_APPROVAL`. Execution Orchestrator ghi activity `APPROVAL_REQUESTED` rồi kết thúc lượt graph hiện tại. Frontend hiển thị yêu cầu phê duyệt dựa trên dữ liệu đã lưu; việc chờ quyết định không yêu cầu giữ LangGraph chạy liên tục hoặc duy trì một HTTP request của Worker.

Chỉ người dùng có permission `Task Management/Approve` mới được gửi quyết định. Backend lấy `user_id` từ access token, không nhận danh tính người phê duyệt tùy ý từ payload. Quyết định được lưu một lần và activity `APPROVAL_APPROVED` hoặc `APPROVAL_REJECTED` được ghi kèm approval ID và người quyết định.

Sau khi ghi nhận một quyết định hợp lệ, API tạo Workflow Job loại `APPROVAL` trong PostgreSQL. Workflow Worker nhận job, tải lại Task bằng `operation_device_id` và gọi `resume_after_approval`. LangGraph bắt đầu một lượt chạy mới với `entry_mode=approval`, rẽ trực tiếp từ START đến node `execute`, không chạy lại `check_gns3`, `plan` hoặc `configure`. Khi không có quyết định và Approval hết hạn, cơ chế xử lý timeout cập nhật các trạng thái nghiệp vụ tương ứng. Approval Gate tính lại hash từ mapping ID và danh sách command hiện tại. Operation WRITE chỉ được thực thi khi trạng thái là `APPROVED`, approval chưa hết hạn, `commands_snapshot` còn nguyên và request hash khớp. Approval `REJECTED` hoặc `EXPIRED` làm mapping chuyển sang `REJECTED`; snapshot hoặc hash không khớp làm mapping chuyển sang `FAILED`. Trong các trường hợp này, Network Agent không được gọi cho mapping đó.

Nếu Task thuộc Benchmark Run, việc resume chỉ hoàn tất Evaluation khi lượt chạy `entry_mode=approval` đã tạo Message `FINAL_RESPONSE`. Một phản hồi yêu cầu phê duyệt không được xem là kết quả benchmark cuối cùng.

```mermaid
flowchart TD
    S([Bắt đầu]) --> A["Approval Gate tra cứu Approval của Device Mapping WRITE"]
    A --> D1{"Đã có Approval?"}
    D1 -->|Không| B["Execution Service tạo Approval PENDING với Commands Snapshot, Hash và thời hạn"]
    B --> C["Approval Gate cập nhật Mapping WAITING_APPROVAL"]
    D1 -->|Có| D2{"Approval đang PENDING?"}
    D2 -->|Có| D3{"Approval còn hạn?"}
    D3 -->|Có| C
    D3 -->|Không| D["Execution Service cập nhật Approval EXPIRED"]
    D --> D0["Approval Gate cập nhật Mapping REJECTED"]
    D0 --> E([Kết thúc])
    D2 -->|Không| D4{"Approval đã APPROVED?"}
    D4 -->|Không| R["Approval Gate cập nhật Mapping REJECTED"]
    R --> E
    D4 -->|Có| D5{"Commands Snapshot và Request Hash khớp?"}
    D5 -->|Không| T["Approval Gate cập nhật Mapping FAILED"]
    T --> E
    D5 -->|Có| U["Network Agent thực thi WRITE qua NetworkTool"]
    U --> V["MappingExecutor cập nhật Mapping và TaskExecution sau WRITE"]
    V --> V1["MappingExecutor lưu DeviceActionLog sau WRITE"]
    V1 --> W["Execution Orchestrator tổng hợp trạng thái Operation và Task"]
    W --> E
    C --> F["Execution Orchestrator ghi APPROVAL_REQUESTED"]
    F --> F1["Execution Orchestrator cập nhật Task RUNNING để chờ duyệt"]
    F1 --> G["Analysis Orchestrator lưu Message APPROVAL_REQUEST"]
    G --> H["Frontend hiển thị yêu cầu phê duyệt"]
    H --> D6{"Người dùng đã gửi quyết định?"}
    D6 -->|Không| D7{"Approval đã hết hạn?"}
    D7 -->|Không| H
    D7 -->|Có| I["Execution Service cập nhật Approval và Task quá hạn"]
    I --> E
    D6 -->|Có| J["API kiểm tra token và quyền Task Management Approve"]
    J --> D8{"Người dùng có quyền Approve?"}
    D8 -->|Không| K["API từ chối yêu cầu quyết định"]
    K --> E
    D8 -->|Có| L["Execution Service kiểm tra trạng thái và thời hạn Approval"]
    L --> D9{"Approval đang PENDING và còn hạn?"}
    D9 -->|Không| M["API trả lỗi Approval không hợp lệ hoặc hết hạn"]
    M --> E
    D9 -->|Có| N0["Execution Service cập nhật Approval với quyết định và người duyệt"]
    N0 --> N["Execution Service ghi APPROVAL_APPROVED hoặc APPROVAL_REJECTED"]
    N --> O["Workflow Job Service tạo Workflow Job APPROVAL trong PostgreSQL"]
    O --> P["Workflow Worker nhận Workflow Job APPROVAL"]
    P --> P1["Execution Orchestrator tải lại Task từ PostgreSQL"]
    P1 --> Q["LangGraph chuyển entry_mode approval từ START đến node execute"]
    Q --> A
```

_Hình 3.8. Sơ đồ hoạt động phê duyệt và tiếp tục thực thi cấu hình._

### 3.6.6. Quy trình kết luận, phản hồi và ghi nhận nhật ký

Sau node `execute`, node `analyze` chỉ tạo kết luận khi Task không còn ở trạng thái đang thực thi hoặc chờ quyết định. Khi workflow đã đủ điều kiện dừng, node `finalize` ghi Evidence Gate cuối cùng, định dạng `AnalysisResult` thành nội dung tiếng Việt dễ đọc và lưu Message loại `FINAL_RESPONSE`. Activity `FINAL_RESPONSE_CREATED` liên kết phản hồi với Task; SSE đóng stream sau khi phát sự kiện `FINAL_RESPONSE_CREATED`; phản hồi `APPROVAL_REQUEST` chỉ thông báo đang chờ phê duyệt và không phải kết quả cuối của Task. Với lỗi ở giai đoạn Planning hoặc Configuration, SSE cũng có thể kết thúc sau activity `TASK_FAILED` tương ứng để giao diện không tiếp tục chờ vô hạn.

Hệ thống sử dụng nhiều nhóm bản ghi có mục đích khác nhau. `task_activity_events` lưu các mốc workflow, actor, trạng thái và sequence phục vụ timeline; `task_executions` lưu từng lần gọi công cụ cùng thời gian và output; `device_action_logs` lưu command thực tế và kết quả theo thiết bị; Approval lưu quyết định của người dùng; `audit_logs` ghi những thao tác quản trị cần kiểm toán ở cấp hệ thống. Các nhật ký này hỗ trợ truy vết nhưng không thay thế việc xác minh trạng thái mạng bằng command READ hoặc điều kiện benchmark.

Structured diagnosis được Analysis Orchestrator lưu trong activity `ANALYSIS_COMPLETED` ở giai đoạn phân tích (mục 3.6.4), trước khi node `finalize` tạo phản hồi và trước khi evaluator đọc kết quả. Dữ liệu bao gồm `is_anomaly`, `root_causes`, `suspected_causes`, Evidence Coverage, lỗi thực thi và thông tin Causal Evidence Gate. Cách lưu này cho phép Benchmark Evaluator chấm submission do Agent tạo ra mà không phải suy diễn root cause từ văn bản phản hồi cuối và không làm rò rỉ Ground Truth vào quá trình chẩn đoán. Riêng Benchmark Run, sau khi Worker nhận được Message `FINAL_RESPONSE`, Benchmark Run Service lưu Evaluation cùng các Metric, liên kết `evaluation_id` và cập nhật Run thành `COMPLETED`; trường `evaluation_result` của Run lưu kết quả RCA, không phải kết quả GOAL.

```mermaid
flowchart TD
    S([Bắt đầu]) --> A["LangGraph chuyển Task và AnalysisResult đến node finalize"]
    A --> D1{"Có AnalysisResult?"}
    D1 -->|Không| B["Analysis Orchestrator lưu Message APPROVAL_REQUEST"]
    B --> E([Kết thúc])
    D1 -->|Có| D2{"Có Evidence Coverage?"}
    D2 -->|Có| C["Analysis Orchestrator ghi EVIDENCE_COVERAGE_EVALUATED và lý do dừng"]
    D2 -->|Không| D["Analysis Orchestrator định dạng AnalysisResult thành phản hồi"]
    C --> D
    D --> F["Conversation Service lưu Message FINAL_RESPONSE và structured_data nếu có"]
    F --> G["Execution Service ghi FINAL_RESPONSE_CREATED liên kết Message và Task"]
    G --> H["API SSE phát FINAL_RESPONSE_CREATED"]
    H --> H1["API SSE đóng stream sau phản hồi cuối"]
    H1 --> E
    G --> D3{"Task thuộc Benchmark Run đang RUNNING?"}
    D3 -->|Không| I["Workflow Worker hoàn tất Workflow Job"]
    D3 -->|Có| J["Benchmark Run Service lưu Evaluation và Evaluation Metrics"]
    J --> K["Benchmark Run Service cập nhật Benchmark Run COMPLETED, Evaluation ID và kết quả RCA"]
    K --> I
    I --> E
```

_Hình 3.9. Sơ đồ hoạt động tạo phản hồi, cập nhật Benchmark Run và phát sự kiện SSE._

### 3.6.7. Quy trình Benchmark Run và khôi phục môi trường

Benchmark Run là quy trình nghiệp vụ bao quanh workflow chẩn đoán. Khi người dùng bắt đầu một Scenario đang hoạt động, Benchmark Service đóng băng toàn bộ Scenario thành `scenario_snapshot`, tạo Run ở trạng thái `PREPARING` và lưu Run trước khi tác động đến topology. Service lần lượt kiểm tra precondition bằng READ, thực thi injection bằng WRITE và kiểm tra `fault_verification`. Nếu toàn bộ bước chuẩn bị thành công, Run chuyển sang `READY` và `cleanup_required=true`.

Khi người dùng bắt đầu Chat từ Run, Conversation và USER_REQUEST được liên kết với Run; Run chuyển sang `RUNNING`. Workflow Multi-Agent xử lý yêu cầu theo cùng quy trình thông thường. Chỉ khi có `FINAL_RESPONSE`, Benchmark Service mới đọc structured diagnosis và các observation đã lưu, tạo `TaskEvaluation` cùng các metric, liên kết Evaluation và Task với Run rồi chuyển Run sang `COMPLETED`. Nếu workflow dừng để chờ approval, Run tiếp tục ở trạng thái `RUNNING` cho đến khi nhánh resume tạo phản hồi cuối.

Nếu precondition, injection hoặc fault verification thất bại, Run chuyển sang `FAILED`. Khi injection đã bắt đầu, hệ thống ưu tiên cleanup trước khi ghi nhận kết quả lỗi; nếu cleanup cũng thất bại, `cleanup_required` vẫn được giữ để cảnh báo môi trường chưa được khôi phục. Cleanup sử dụng các action trong snapshot, mở kết nối mới cho mỗi lần thử, tạo READ check tương ứng và chỉ đánh dấu `CLEANED` sau khi trạng thái phục hồi được xác minh. Cơ chế retry có giới hạn; khi hết số lần thử, Run không được xem là đã cleanup thành công. Thiết kế chi tiết Scenario, action, Ground Truth và evaluator được trình bày tiếp tại mục 3.9.

```mermaid
stateDiagram-v2
    [*] --> PREPARING: Bắt đầu Scenario
    PREPARING --> READY: Precondition, injection và verification thành công
    PREPARING --> FAILED: Chuẩn bị hoặc verification thất bại
    READY --> RUNNING: Liên kết Conversation và USER_REQUEST
    RUNNING --> RUNNING: Chờ approval hoặc workflow tiếp tục
    RUNNING --> COMPLETED: Có FINAL_RESPONSE và Evaluation
    RUNNING --> FAILED: Workflow thất bại
    COMPLETED --> CLEANED: Cleanup và READ verification thành công
    FAILED --> CLEANED: Cleanup bắt buộc thành công
    CLEANED --> [*]
```

_Hình 3.10. Vòng đời Benchmark Run và điều kiện khôi phục môi trường._

## 3.7. Thiết kế dữ liệu và cơ sở dữ liệu

### 3.7.1. Mô hình dữ liệu và sơ đồ ERD

PostgreSQL quản lý dữ liệu theo các miền Identity, Inventory, Conversation, Execution, Benchmark, Evaluation và Audit. Các thực thể được liên kết bằng khóa ngoại để truy vết từ yêu cầu người dùng đến Task, kế hoạch, lần thực thi, hành động trên thiết bị và kết quả đánh giá.

```mermaid
erDiagram
    USERS ||--o{ CONVERSATIONS : owns
    USERS ||--o{ USER_SESSIONS : has
    USERS }o--o{ ROLES : assigned
    ROLES }o--o{ PERMISSIONS : grants
    CREDENTIALS ||--o{ DEVICES : authenticates
    BRANDS ||--o{ DEVICES : classifies
    CATEGORIES ||--o{ DEVICES : groups
    CONVERSATIONS ||--o{ MESSAGES : contains
    CONVERSATIONS ||--o{ TASKS : creates
    TASKS ||--o{ TASK_OPERATIONS : contains
    TASK_OPERATIONS ||--o{ OPERATION_DEPENDENCIES : depends
    TASK_OPERATIONS ||--o{ TASK_OPERATION_DEVICES : targets
    DEVICES ||--o{ TASK_OPERATION_DEVICES : assigned
    TASKS ||--o{ TASK_EXECUTIONS : records
    TASKS ||--o{ TASK_ACTIVITY_EVENTS : emits
    TASKS ||--o{ DEVICE_ACTION_LOGS : logs
    BENCHMARK_SCENARIOS ||--o{ BENCHMARK_RUNS : instantiates
    BENCHMARK_RUNS }o--o| TASKS : evaluates
    TASKS ||--o| TASK_EVALUATIONS : receives
    TASK_EVALUATIONS ||--o{ TASK_EVALUATION_METRICS : contains
    USERS ||--o{ AUDIT_LOGS : acts
```

_Hình 3.11. Sơ đồ quan hệ thực thể rút gọn của hệ thống._

### 3.7.2. Quản lý thiết bị và thông tin kết nối

Inventory được chuẩn hóa thành Brand, Category, Credential và Device. Thiết bị chứa hostname, host/port, driver và liên kết credential. Password và enable secret được mã hóa khi lưu; chỉ lớp kết nối nội bộ được giải mã khi cần. Planner và frontend không nhận plaintext hoặc ciphertext của thông tin xác thực.

### 3.7.3. Quản lý Task, Operation và Execution

Task đại diện cho nhiệm vụ phát sinh từ yêu cầu người dùng. Mỗi Task chứa nhiều Operation; dependency biểu diễn điều kiện thực thi giữa các Operation; bảng ánh xạ Operation–Device quản lý vai trò, access mode và trạng thái trên từng thiết bị. Task Execution lưu từng lần thực thi, Device Action Log ghi lệnh và output, còn Task Activity Event ghi các sự kiện quan trọng trong vòng đời nhiệm vụ.

### 3.7.4. Quản lý kết quả đánh giá và Audit Log

Benchmark Scenario mô tả kịch bản, trạng thái ban đầu, injection, Ground Truth và cleanup; Benchmark Run đại diện cho một lần chạy độc lập. Task Evaluation và Evaluation Metric lưu điểm, giá trị mong đợi, giá trị thực tế và bằng chứng. Audit Log ghi các thao tác nghiệp vụ cần kiểm toán độc lập với phản hồi ngôn ngữ tự nhiên của Agent.

## 3.8. Xây dựng và triển khai hệ thống

### 3.8.1. Xây dựng Backend và API

Backend được phát triển bằng FastAPI và tổ chức theo domain. Router tiếp nhận HTTP request và kiểm tra quyền; Service thực hiện logic nghiệp vụ; Repository truy xuất dữ liệu; Schema và Model định nghĩa hợp đồng dữ liệu. Các Agent không trực tiếp thao tác ORM hoặc cơ sở dữ liệu.

### 3.8.2. Xây dựng giao diện quản trị

Frontend được xây dựng bằng React 19, TypeScript, Vite, Tailwind CSS và hệ component shadcn; sử dụng các thư viện bảng, form, trạng thái và giao tiếp HTTP phù hợp. Các feature hiện có gồm Login/Profile, Dashboard, Chatbot/Conversation, Tasks, Devices, Credentials, Device Catalog, Users, Roles/Access Control, Audit Logs, Benchmark Scenarios, Benchmark Runs và Evaluations. Giao diện chat hỗ trợ danh sách hội thoại, activity timeline, hiển thị yêu cầu approval và mở chi tiết Task; trang Benchmark hỗ trợ nhập action/check/Ground Truth và xem kết quả chạy.

Trang Evaluations hiển thị lịch sử đánh giá, GOAL/RCA, Remediation/Safety, Latency và Interaction Turns, cùng các kết quả có cấu trúc của v4 gồm RCA F1, Precision, Recall, Localization F1, Fault Type F1 và Detection. Dashboard dùng `GET /benchmarks/runs/summary` làm nguồn chuẩn cho TSR toàn bộ lịch sử. Khi lọc theo ngày bắt đầu Benchmark Run, frontend phân loại tập Run theo cùng quy tắc backend và tra kết quả `GOAL` từ Evaluation liên kết, không dùng `BenchmarkRun.evaluation_result` để tính TSR vì trường này hiện lưu kết quả **RCA**, không phải GOAL. GOAL Pass Rate, RCA Pass Rate và RCA F1 được hiển thị riêng với mẫu số tương ứng. Phiên bản evaluator giúp phân biệt chấm từ khóa lịch sử và chấm RCA có cấu trúc.

### 3.8.3. Tích hợp LLM và các công cụ mạng

Planner Agent và Analyst Agent gọi LLM qua NVIDIA AI Endpoint; phản hồi được kiểm tra bằng Pydantic trước khi chuyển sang bước tiếp theo. Network Agent sử dụng `NetworkTool` thay vì gọi LLM, nhờ đó quyền thực thi lệnh được giữ tại tầng ứng dụng. Các thư viện I/O đồng bộ được gọi theo cách không chặn vòng lặp bất đồng bộ của FastAPI.

### 3.8.4. Triển khai và cấu hình môi trường

FastAPI API, Workflow Worker, PostgreSQL, migration và pgAdmin được tổ chức bằng Docker Compose. Cấu hình kết nối cơ sở dữ liệu, khóa xác thực, LLM provider và network backend được quản lý qua biến môi trường. Frontend chạy bằng Vite trong quá trình phát triển và kết nối REST API bằng access token. GNS3 Server hoạt động như môi trường thực nghiệm bên ngoài các dịch vụ nghiệp vụ.

### 3.8.5. Giao diện các nhóm API

| Nhóm API     | Chức năng chính                                           |
| ------------ | --------------------------------------------------------- |
| Identity     | Đăng nhập, phiên, người dùng, vai trò và quyền truy cập   |
| Inventory    | Thiết bị, danh mục thiết bị và credential kết nối         |
| Conversation | Hội thoại, tin nhắn và yêu cầu xử lý AI                   |
| Execution    | Task, Operation, kết quả thực thi và quyết định phê duyệt |
| Benchmark    | Scenario, Benchmark Run và Cleanup                        |
| Evaluation   | Kết quả đánh giá và các metric                            |
| Audit        | Nhật ký kiểm toán và bộ lọc tra cứu                       |

Các API nghiệp vụ dùng tiền tố `/api/v1`. Frontend không trực tiếp kết nối thiết bị; mọi thao tác được chuyển đến Service và Orchestrator tương ứng. FastAPI cung cấp thêm health endpoint và tài liệu OpenAPI phục vụ phát triển, kiểm thử tích hợp.

## 3.9. Thiết kế hệ thống thực nghiệm và đánh giá

### 3.9.1. Thiết kế Benchmark Scenario và Ground Truth

Benchmark Scenario có `scenario_key`, version, mô tả, topology, initial_message, preconditions, injection, fault_verification, ground_truth, evaluation_required_terms và cleanup. Engine thực hiện kiểm tra điều kiện trước; tiêm lỗi bằng các action có schema; xác minh trạng thái sự cố; sau đó phát hành run sẵn sàng để Chat của Agent giải quyết. Khi bắt đầu Chat, run liên kết tới conversation/source message; khi nhận FINAL_RESPONSE, lưu Evaluation và hoàn tất run. Cleanup được retry có giới hạn bằng kết nối mới và chỉ hoàn tất sau khi READ check suy ra từ action xác nhận thiết bị đã phục hồi; runner dừng nếu không thể xác nhận nhằm bảo toàn tính độc lập giữa các kịch bản. Cơ chế này có thể quản lý scenario, lịch sử và trạng thái chuẩn bị/chạy/hoàn thành/thất bại/cleanup.

### 3.9.2. Quy trình tiêm lỗi, kiểm thử và khôi phục môi trường

Các nhóm injection đã có bộ dựng command bao gồm shutdown/no shutdown interface, điều chỉnh network OSPF, MPLS trên interface, default route, IP/mask, ACL và BGP neighbor shutdown/no shutdown. Có các seed chứa các tình huống interface down, OSPF, MPLS, cấu hình IP, ACL, Loopback0 và BGP. Sự hiện diện của seed/chương trình dựng command **không mặc nhiên xác nhận đã chạy thành công tất cả scenario trong lab**.

Quy trình thực nghiệm gồm kiểm tra precondition, tiêm lỗi, xác minh fault, gửi yêu cầu cho hệ thống Multi-Agent, thu thập kết quả, chấm điểm và cleanup. Nếu không xác minh được trạng thái khôi phục, runner dừng trước kịch bản tiếp theo để tránh làm sai lệch dữ liệu.

### 3.9.3. Cơ chế thu thập và đánh giá kết quả

Ground Truth được lưu ở snapshot của lần chạy để việc cập nhật scenario về sau không thay đổi căn cứ chấm của run cũ. `BenchmarkObservationRepository` đọc kết luận Agent từ Activity Event `ANALYSIS_COMPLETED`, đếm các lần Agent gọi tool và lấy mốc timestamp để tính thời gian. Evaluator v4 xuất dữ liệu từng metric với `expected_value`, `actual_value`, `evidence`; lưu vào các bảng Evaluation và metric, kết quả API chỉ đọc được người có quyền truy cập yêu cầu. TSR được tổng hợp bằng truy vấn SQL từ toàn bộ Benchmark Run, không lấy mẫu chỉ theo các dòng giao diện đã tải.

### 3.9.4. Quy tắc tính toán các chỉ số đánh giá

Cần phân biệt **GOAL Pass Rate trên các Run đã được chấm** với **Task Success Rate (TSR) của API tổng hợp**. Hai chỉ số có mẫu số khác nhau khi workflow thất bại trước khi Evaluation được lưu.

**GOAL Pass Rate (Run đã được chấm):**

$$
GOALPassRate=\frac{N_{\mathrm{GOAL\ PASS}}}{N_{\mathrm{GOAL\ PASS}}+N_{\mathrm{GOAL\ FAIL}}}\times100\%.
$$

Chỉ các Evaluation có GOAL PASS hoặc GOAL FAIL được đưa vào mẫu số này. Báo cáo cũng trình bày tỷ lệ `GOAL PASS / tổng số Run` để không che giấu các lượt chưa được chấm.

**TSR theo API `GET /benchmarks/runs/summary`:**

$$
TSR_{\mathrm{API}}=\frac{N_{\mathrm{passed}}}{N_{\mathrm{passed}}+N_{\mathrm{failed}}}\times100\%.
$$

Quy tắc `classify_run` ở `src/app/domains/benchmark/utils/summary.py` xác định: `passed` là Run `COMPLETED/CLEANED` có Evaluation GOAL PASS; `failed` là Run `COMPLETED/CLEANED` có GOAL FAIL, hoặc Run `FAILED` sau khi Agent Chat bắt đầu, hoặc Run đã hoàn tất có `source_message_id` và `error_message` nhưng chưa lưu GOAL. `not_started`, `in_progress`, `setup_failed` và `unscored` không thuộc mẫu số. Cleanup không làm thay đổi kết quả GOAL. Khi không có Run hợp lệ, API trả `success_rate=null` thay vì 0%.

`BenchmarkRun.evaluation_result` hiện lưu RCA, không phải GOAL. Dashboard toàn bộ lịch sử lấy thống kê từ API summary; Dashboard lọc ngày dùng kết quả GOAL của Evaluation và cùng quy tắc phân loại Run. Khi công bố tỷ lệ cần ghi số Run tổng, số được chấm, số thất bại khi thực thi và mẫu số thực tế.

Với RCA, gọi $P$ là tập cặp tài nguyên–loại lỗi dự đoán và $G$ là Ground Truth:

$$
TP=|P\cap G|,\qquad FP=|P-G|,\qquad FN=|G-P|
$$

$$
Precision=\frac{TP}{TP+FP},\qquad Recall=\frac{TP}{TP+FN}
$$

$$
F1=\frac{2\times Precision\times Recall}{Precision+Recall}
$$

Active Latency được tính từ thời điểm tạo Task đến phản hồi cuối, sau khi loại trừ các khoảng chờ phê duyệt hợp lệ:

$$
T_{active}=T_{final}-T_{task}-T_{approval}
$$

Interaction Turns là số lần Agent gọi công cụ trong phạm vi Task, không phải số tin nhắn hoặc số bước suy luận nội bộ. Remediation và Safety chỉ được ghi PASS/FAIL khi có bộ chấm và bằng chứng tương ứng; nếu chưa triển khai đầy đủ, metric phải được phân loại NOT_APPLICABLE.

---

# CHƯƠNG 4. THỰC NGHIỆM VÀ ĐÁNH GIÁ

Chương này trình bày quá trình thực nghiệm hệ thống Multi-Agent trên môi trường mạng giả lập GNS3 và đánh giá kết quả bằng dữ liệu được lưu trong cơ sở dữ liệu. Nội dung tập trung vào ba khía cạnh: khả năng hoàn thành nhiệm vụ chẩn đoán, độ chính xác của kết luận nguyên nhân gốc và chi phí thực thi. Kết quả kiểm thử phần mềm được phân biệt với kết quả thực nghiệm của Agent; các chỉ số chỉ được công bố khi có Benchmark Run và Evaluation tương ứng.

## 4.1. Mục tiêu và câu hỏi thực nghiệm

### 4.1.1. Mục tiêu thực nghiệm

Thực nghiệm được xây dựng nhằm xác định mức độ đáp ứng của hệ thống đối với nhiệm vụ chẩn đoán sự cố mạng bằng ngôn ngữ tự nhiên. Một lượt thực nghiệm bao gồm việc chuẩn bị môi trường, tiêm sự cố, gửi yêu cầu đến hệ thống Multi-Agent, thu thập kết luận có cấu trúc, đối chiếu với Ground Truth và khôi phục topology về trạng thái ban đầu.

Các mục tiêu cụ thể gồm:

- Kiểm tra khả năng vận hành xuyên suốt của chuỗi Planner Agent, Network Agent, Analyst Agent và các Orchestrator.
- Đánh giá khả năng phát hiện bất thường, định vị thiết bị hoặc interface xảy ra lỗi và xác định đúng loại nguyên nhân.
- Đo tỷ lệ hoàn thành mục tiêu, thời gian workflow hoạt động và số lượt gọi công cụ mạng.
- Quan sát ảnh hưởng của các thay đổi về playbook, Evidence Gate, investigation loop và bộ phân tích bằng chứng đối với kết quả chẩn đoán.
- Kiểm tra việc cô lập từng lượt chạy và khả năng cleanup môi trường sau thực nghiệm.

### 4.1.2. Câu hỏi nghiên cứu

Bảng 4.1 trình bày các câu hỏi được sử dụng để định hướng quá trình đánh giá.

| Mã | Câu hỏi nghiên cứu | Chỉ số sử dụng |
| --- | --- | --- |
| RQ1 | Hệ thống hoàn thành đúng mục tiêu chẩn đoán với tỷ lệ như thế nào? | GOAL Pass, Task Success Rate |
| RQ2 | Hệ thống phát hiện, định vị và xác định nguyên nhân gốc chính xác đến đâu? | Detection Score, Localization Precision/Recall/F1, Fault Type Precision/Recall/F1, RCA Precision/Recall/F1 |
| RQ3 | Việc bổ sung bằng chứng và điều tra lặp ảnh hưởng như thế nào đến kết quả? | Evidence Coverage, số trường hợp chuyển từ FAIL sang PASS, Interaction Turns |
| RQ4 | Chi phí xử lý của workflow là bao nhiêu? | Active Latency trung bình, trung vị và Interaction Turns |
| RQ5 | Hệ thống có bảo đảm kiểm soát thay đổi và khôi phục môi trường thử nghiệm không? | Trạng thái Approval, Cleanup và `cleanup_required` |

### 4.1.3. Phạm vi đánh giá

Thực nghiệm được thực hiện trên một topology GNS3 dùng Cisco IOS, gồm các nhóm thiết bị Provider, Provider Edge và Customer Edge. Tập kịch bản tập trung vào lỗi interface, địa chỉ IP, OSPF, MPLS, BGP và ACL. Hệ thống sử dụng LLM qua NVIDIA API nhưng không huấn luyện hoặc fine-tune mô hình.

Kết quả trong chương này phản ánh khả năng của hệ thống trên topology, tập scenario, prompt, model và evaluator đã chọn. Kết quả chưa đại diện cho mọi thiết bị, nhà sản xuất hoặc sự cố trong mạng thực tế. Mỗi scenario mới được quan sát một lần trong từng cohort theo ngày logic; vì vậy phần so sánh mang tính mô tả, chưa phải kiểm định thống kê về quan hệ nhân quả.

## 4.2. Môi trường thực nghiệm

### 4.2.1. Thành phần phần mềm

Môi trường thực nghiệm gồm ứng dụng web, API, tiến trình xử lý workflow, cơ sở dữ liệu và GNS3. Các thành phần chính được trình bày trong Bảng 4.2.

| Thành phần | Công nghệ và vai trò |
| --- | --- |
| Frontend | React 19, TypeScript và Vite; khởi tạo Benchmark Run, theo dõi Chat, Task, Approval và Evaluation |
| Backend API | Python, FastAPI, Pydantic và SQLAlchemy; cung cấp REST API, SSE và dịch vụ nghiệp vụ |
| Workflow Worker | Tiến trình nền lấy durable workflow job và chạy LangGraph ngoài request HTTP |
| Multi-Agent | Planner Agent, Configuration Agent, Network Agent, Analyst Agent và các Orchestrator |
| Điều phối | LangGraph; tổ chức các node `check_gns3`, `plan`, `configure`, `execute`, `analyze`, `investigate` và `finalize` |
| Thực thi mạng | NetworkTool sử dụng Netmiko hoặc Nornir để thao tác CLI trên Cisco IOS |
| Cơ sở dữ liệu | PostgreSQL; lưu Scenario, Run, Conversation, Task, Activity, Execution, Evaluation và Metric |
| Môi trường mạng | GNS3; cung cấp topology và console thiết bị cho quá trình tiêm lỗi, chẩn đoán và cleanup |
| Triển khai | Docker Compose cho API, Workflow Worker, PostgreSQL, migration và các dịch vụ hỗ trợ |

Thông số phần cứng của máy chạy chưa được đóng băng thành metadata của từng Benchmark Run, do đó chương này không sử dụng kết quả để so sánh hiệu năng phần cứng. Các số đo thời gian chỉ được diễn giải trong phạm vi môi trường phát triển đã sử dụng.

### 4.2.2. Topology mạng

Topology thực nghiệm mô phỏng mạng lõi MPLS, trong đó OSPF cung cấp khả năng định tuyến nội miền, MPLS/LDP phục vụ chuyển tiếp nhãn và eBGP kết nối các thiết bị CE với PE. Các thiết bị được quản lý trong Inventory và ánh xạ đến node GNS3 tương ứng.

![Network Topology](../images/network-topology.png)

_Hình 4.1. Topology mạng thực nghiệm trên GNS3._

Topology cho phép đặt lỗi tại nhiều lớp khác nhau: trạng thái vật lý hoặc quản trị của interface, địa chỉ IP, OSPF network/area, MPLS trên interface, BGP neighbor và ACL. Trước khi tiêm lỗi, Benchmark Engine thực hiện precondition; sau khi tiêm, `fault_verification` xác nhận lỗi thực sự tồn tại. Run chỉ chuyển sang `READY` khi hai bước này thành công.

### 4.2.3. Cấu hình Agent

Planner Agent và Analyst Agent sử dụng LLM được cấu hình qua NVIDIA API. Dữ liệu LLM trả về phải vượt qua Pydantic schema và validation nghiệp vụ trước khi được sử dụng. Các tham số điều khiển chính được trình bày trong Bảng 4.3.

| Tham số | Giá trị cấu hình mặc định |
| --- | ---: |
| Planner timeout | 90 giây |
| Analyst timeout | 120 giây |
| Planner validation retries | 2 |
| Analyst validation retries | 2 |
| Analyst maximum completion tokens | 4096 |
| Số vòng investigation tối đa | 2 |
| Ngưỡng diagnosis confidence | 0,8 |
| Số message lịch sử cung cấp cho Planner | 5 |

Tên model được quản lý bằng biến môi trường và phải được ghi kèm metadata khi tái lập thực nghiệm. Các cohort trong báo cáo được chạy trên cùng pipeline ứng dụng, nhưng mã nguồn đã được cải tiến theo từng ngày logic như trình bày tại Mục 4.6.

**Bảng 4.3a. Metadata cần đóng băng để tái lập các cohort**

| Trường | Điều xác nhận được từ mã nguồn | Trạng thái của dữ liệu thực nghiệm lịch sử |
| --- | --- | --- |
| Tên model NVIDIA thực tế | Planner, Configuration và Analyst cùng đọc `settings.nvidia_model` / `NVIDIA_MODEL` bằng `ChatNVIDIA`; `.env.example` chỉ có giá trị placeholder | **Chưa được xác nhận** trong metadata Run hoặc repository; cần lấy từ manifest/log của thời điểm chạy |
| Tham số inference | `temperature=0`, `enable_thinking=False`, `parallel_tool_calls=False` trong `src/app/agents/dependencies.py` | Là cấu hình của code đang đối chiếu; không chứng minh các cohort lịch sử có cùng cấu hình |
| Prompt version | Prompt tại `planner/prompts.py`, `configuration/prompts.py`, `analyst/prompts.py` | Chưa có prompt hash hoặc prompt version gắn với từng Run; cần lấy SHA của từng file theo commit chạy |
| Git commit theo cohort | Commit đối chiếu báo cáo: backend `5e9f0815a0`, frontend `d96e94f197` | **Không phải** commit đã được xác nhận chạy các cohort ngày logic 27/10–02/11; cần đối chiếu lịch sử triển khai |
| Evaluator version | Báo cáo có v4/v5; `build_benchmark_evaluation` hiện lưu `db-benchmark-v5` | Ghi evaluator version theo từng Run, không gộp rubric khác nhau để suy luận tác động |
| Network backend | `NETWORK_BACKEND=netmiko` là mặc định, Nornir là lựa chọn khác | Adapter dùng trong từng cohort, phiên bản Cisco IOS/image và cấu hình node chưa được lưu kèm Run |
| Môi trường | Docker Compose, FastAPI, LangGraph, PostgreSQL, GNS3 | CPU/RAM/OS, phiên bản Python, dependency lock, GNS3/IOS và điều kiện tải thực tế chưa được đóng băng |

Bảng 4.3a phân biệt **giá trị code có thể kiểm tra** với **giá trị đã được ghi nhận thực sự khi thực nghiệm**. Không điền tên model, prompt SHA, commit lịch sử hoặc cấu hình phần cứng bằng suy đoán. Trước khi tái công bố số liệu, cần tạo manifest cho mỗi cohort gồm thời điểm chạy thật, ngày logic, model ID, prompt SHA, backend commit, evaluator, topology/image, adapter, hardware và các tham số suy luận. Manifest không chứa khóa API hoặc credential.

## 4.3. Thiết kế kịch bản và quy trình thực nghiệm

### 4.3.1. Cấu trúc Benchmark Scenario

Mỗi Benchmark Scenario là một đặc tả có phiên bản, bao gồm:

- Thông tin nhận dạng: `scenario_key`, tên, version và topology.
- `initial_message`: yêu cầu chẩn đoán được gửi vào Chat.
- `preconditions`: các phép kiểm tra READ xác nhận trạng thái ban đầu.
- `injection`: thao tác tạo sự cố trên thiết bị.
- `fault_verification`: kiểm tra sự cố đã được tiêm thành công.
- `ground_truth`: danh sách nguyên nhân đúng gồm device, interface và `fault_type`.
- `cleanup`: thao tác phục hồi trạng thái môi trường.

Khi bắt đầu thực nghiệm, toàn bộ nội dung scenario được sao chép vào `scenario_snapshot` của Benchmark Run. Nhờ đó, việc sửa seed hoặc scenario sau này không làm thay đổi Ground Truth của lượt chạy đã hoàn tất.

### 4.3.2. Tập dữ liệu thực nghiệm

Cơ sở dữ liệu có 33 scenario, trong đó 32 scenario ở trạng thái active và được sử dụng cho mỗi cohort đầy đủ. Phân bố Ground Truth của cohort ngày 02/11/2026 được trình bày trong Bảng 4.4.

| Loại sự cố | Số scenario |
| --- | ---: |
| `link_down` | 8 |
| `bgp_neighbor_admin_down` | 6 |
| `mpls_disabled` | 5 |
| `ospf_network_missing` | 4 |
| `acl_traffic_block` | 3 |
| `ospf_area_mismatch` | 2 |
| `wrong_ip_address` | 2 |
| `loopback_admin_down` | 1 |
| `wrong_subnet_mask` | 1 |
| **Tổng cộng** | **32** |

Tập dữ liệu do đề tài xây dựng cho topology GNS3 hiện có; đây không phải dataset được nhập trực tiếp từ NIKA. Đề tài chỉ tham khảo cách biểu diễn Ground Truth và cách đánh giá RCA theo tập nguyên nhân.

### 4.3.3. Quy trình chạy một scenario

Một lượt chạy được thực hiện theo trình tự sau:

1. Tạo Benchmark Run ở trạng thái `PREPARING` và lưu snapshot của scenario.
2. Kiểm tra precondition trên thiết bị.
3. Thực hiện injection và xác minh sự cố.
4. Chuyển Run sang `READY`, tạo Conversation và gửi `initial_message`.
5. Workflow Multi-Agent lập kế hoạch, thu thập bằng chứng, phân tích và tạo `FINAL_RESPONSE`.
6. Evaluator lấy structured diagnosis từ activity, đối chiếu với Ground Truth và lưu Task Evaluation cùng các metric.
7. Thực hiện cleanup, kiểm tra lại trạng thái và chuyển Run sang `CLEANED` nếu thành công.
8. Với chạy backfill, đồng bộ timestamp của các bản ghi liên quan về ngày logic được truyền vào runner.

```mermaid
stateDiagram-v2
    [*] --> PREPARING
    PREPARING --> READY: Precondition, injection và verification đạt
    PREPARING --> FAILED: Không chuẩn bị được môi trường
    READY --> RUNNING: Gửi yêu cầu vào Chat
    RUNNING --> COMPLETED: Có FINAL_RESPONSE và Evaluation
    RUNNING --> FAILED: Workflow không hoàn tất
    COMPLETED --> CLEANED: Cleanup và hậu kiểm đạt
    FAILED --> CLEANED: Cleanup sau lỗi đạt
    CLEANED --> [*]
```

_Hình 4.2. Vòng đời một Benchmark Run._

### 4.3.4. Kiểm soát tính độc lập và tái lập

Các scenario được chạy tuần tự; giữa hai lượt có khoảng cooldown 15 giây. Runner chỉ chuyển sang scenario tiếp theo sau khi xử lý cleanup của lượt hiện tại. Trường hợp `cleanup_required=true` được xem là môi trường chưa an toàn để tiếp tục và cần được xử lý trước khi chạy lại.

Các cohort được gắn ngày logic bằng cơ chế backfill. Ngày logic phục vụ việc so sánh và hiển thị thống kê; nó không phải thời điểm commit hoặc thời gian đồng hồ thực của tiến trình. Khi diễn giải kết quả phải đối chiếu đồng thời ngày logic, evaluator version và thay đổi mã nguồn tương ứng.

**Giới hạn ngữ cảnh đầu vào.** Một số `initial_message` trong seed nêu sẵn thiết bị, interface hoặc giao thức nghi vấn (chẳng hạn yêu cầu chẩn đoán MPLS/LDP tại một interface). Agent không được cung cấp trực tiếp tập Ground Truth `(resource_id, fault_type)`, nhưng gợi ý làm hẹp không gian tìm kiếm. Vì vậy kết quả hiện tại phản ánh **chẩn đoán có ngữ cảnh ban đầu**, chưa thể hiện khả năng tự phát hiện/định vị sự cố hoàn toàn không gợi ý. Đánh giá tiếp theo cần thêm cặp prompt có gợi ý và không gợi ý trên cùng trạng thái lỗi, Ground Truth và evaluator, tránh gộp hai mức khó vào cùng một tỷ lệ mà không phân nhóm.

## 4.4. Tiêu chí và phương pháp đánh giá

### 4.4.1. Biểu diễn kết luận có cấu trúc

Analyst Agent tạo structured diagnosis gồm `is_anomaly` và danh sách `root_causes`. Mỗi nguyên nhân được chuẩn hóa thành cặp:

```text
(resource_id, fault_type)
```

Lỗi interface sử dụng định danh `interface/<device>/<interface>`; lỗi cấp thiết bị sử dụng `node/<device>`. Bộ chấm không tìm kiếm từ khóa trong phản hồi cuối để suy diễn nguyên nhân. Vì vậy, việc Agent nhắc đúng tên thiết bị nhưng kết luận sai không được tính là RCA đúng.

Gọi `G` là tập nguyên nhân trong Ground Truth và `P` là tập dự đoán của Agent:

```text
TP = |P ∩ G|
FP = |P - G|
FN = |G - P|

Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
F1        = 2 × Precision × Recall / (Precision + Recall)
```

RCA yêu cầu khớp đồng thời tài nguyên và loại lỗi. Localization chỉ so sánh tài nguyên; Fault Type chỉ so sánh loại lỗi. Việc tách ba nhóm chỉ số giúp xác định Agent sai ở bước định vị hay phân loại nguyên nhân.

### 4.4.2. Detection, GOAL và Task Success Rate

Detection Score bằng 1 khi Agent nhận biết đúng trạng thái bất thường. Do toàn bộ scenario trong tập hiện tại đều được tạo bằng cách tiêm lỗi, Ground Truth `is_anomaly` là true. Vì chưa có mẫu negative với mạng khỏe, chỉ số này không được diễn giải là Detection Accuracy trên một dataset cân bằng.

Một Run đạt `GOAL PASS` khi Agent đồng thời nhận biết bất thường và tập nguyên nhân dự đoán exact-match Ground Truth. **GOAL Pass Rate trên các Run đã được chấm** được tính như sau:

```text
GOAL Pass Rate = số Run GOAL PASS / số Run có kết quả GOAL hợp lệ
```

Run lỗi ở bước chuẩn bị môi trường không được xem là thất bại chẩn đoán của Agent. Run đã chạy Agent nhưng chưa có Evaluation cần được báo cáo riêng: nếu Run chuyển `FAILED` sau khi bắt đầu Chat, API tính vào `failed`; nếu Run hoàn tất nhưng thiếu GOAL và không có lỗi dứt điểm, API xếp `unscored` và loại khỏi mẫu số. Vì vậy GOAL Pass Rate của các Run được chấm có thể khác TSR của API; cần trình bày cả hai kèm số mẫu.

### 4.4.3. Latency và Interaction Turns

Active Latency được tính từ thời điểm tạo Task đến khi tạo phản hồi cuối, sau khi loại trừ hợp các khoảng chờ người dùng phê duyệt:

```text
T_active = T_final_response - T_task_created - T_waiting_for_approval
```

Chỉ số này bao gồm thời gian Planner, NetworkTool, Analyst, Orchestrator và truy cập dữ liệu; không bao gồm thời gian injection, cleanup và thời gian chờ phê duyệt. Vì vậy đây là thời gian hoạt động của workflow AI, không phải thời gian suy luận thuần của LLM.

Interaction Turns là số lần gọi công cụ có bản ghi trong `task_executions`. Chỉ số thấp không mặc nhiên tốt hơn, vì quá ít lượt có thể dẫn đến thiếu bằng chứng; chỉ số này phải được xem cùng RCA và Evidence Coverage.

### 4.4.4. Phiên bản evaluator

`db-benchmark-v4` chuyển từ cách chấm từ khóa sang so sánh structured diagnosis. `db-benchmark-v5` tiếp tục sử dụng phép so sánh tập hợp nhưng bổ sung taxonomy `FaultType` đóng và chuẩn hóa alias. Vì rubric thay đổi, số liệu giữa các evaluator chỉ được dùng để mô tả xu hướng của toàn pipeline; khi thực hiện kiểm định chính thức cần chạy lại các cohort bằng cùng một evaluator version.

## 4.5. Kết quả thực nghiệm

### 4.5.1. Kết quả tổng hợp theo cohort

Bảy cohort đầy đủ từ ngày logic 27/10 đến 02/11/2026 tạo ra tổng cộng 224 Benchmark Run. Mỗi cohort gồm cùng 32 scenario active. Bảng 4.5 thể hiện số liệu đã tổng hợp từ `benchmark_runs`, `task_evaluations` và `task_evaluation_metrics` trên môi trường thực nghiệm của nhóm. Chưa có bản xuất kết quả thô và script tổng hợp được lưu kèm repo để người đọc kiểm chứng độc lập; không xem bảng này là kết quả chạy lại trên commit đối chiếu. `PASS/Run` lấy toàn bộ 32 Run làm mẫu số, còn `PASS/được chấm` chỉ lấy Evaluation có GOAL hợp lệ; cả hai đều cần phân biệt với TSR API khi có lỗi thực thi chưa chấm.

| Ngày logic | Run | Được chấm | GOAL PASS | PASS/Run | PASS/được chấm | RCA F1 TB | Localization F1 TB | Fault Type F1 TB | Detection TB | Latency TB (s) | Trung vị (s) | Turns TB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 27/10 | 32 | 30 | 11 | 34,38% | 36,67% | 0,4444 | 0,4444 | 0,5111 | 0,5667 | 34,89 | 32,17 | 6,40 |
| 28/10 | 32 | 30 | 14 | 43,75% | 46,67% | 0,5278 | 0,5944 | 0,6333 | 0,8000 | 38,53 | 31,79 | 6,40 |
| 29/10 | 32 | 31 | 14 | 43,75% | 45,16% | 0,5161 | 0,5161 | 0,5806 | 0,7097 | 44,50 | 36,88 | 6,74 |
| 30/10 | 32 | 31 | 20 | 62,50% | 64,52% | 0,6828 | 0,6828 | 0,7097 | 0,7742 | 27,44 | 28,46 | 4,45 |
| 31/10 | 32 | 31 | 23 | 71,88% | 74,19% | 0,7419 | 0,7419 | 0,7419 | 0,8065 | 29,47 | 24,37 | 4,19 |
| 01/11 | 32 | 32 | 29 | 90,63% | 90,63% | 0,9063 | 0,9063 | 0,9063 | 0,9375 | 42,44 | 35,49 | 4,38 |
| 02/11 | 32 | 32 | **31** | **96,88%** | **96,88%** | **0,9688** | **0,9688** | **0,9688** | **0,9688** | 35,95 | 32,82 | 4,69 |

Kết quả cho thấy tỷ lệ GOAL PASS tăng từ 11/32 ở baseline ngày 27/10 lên 31/32 ngày 02/11, tương ứng tăng 62,50 điểm phần trăm trên toàn cohort. RCA F1 trung bình tăng từ 0,4444 lên 0,9688. Đồng thời, Interaction Turns trung bình giảm từ 6,40 xuống 4,69. Xu hướng đồng thời về GOAL PASS, RCA F1 và Interaction Turns phù hợp với giả thuyết pipeline sau cải tiến xử lý bằng chứng tốt hơn, nhưng đây chỉ là **quan sát theo cohort**, không xác lập quan hệ nhân quả vì nhiều thành phần và cả evaluator đã thay đổi giữa các cohort.

### 4.5.2. Trả lời RQ1 – Khả năng hoàn thành nhiệm vụ

Ở cohort ngày 02/11, toàn bộ 32 Run đều tạo được Evaluation; 31 Run đạt GOAL PASS và một Run GOAL FAIL. TSR của cohort là 96,88%. So với ngày 27/10, số Run được chấm tăng từ 30 lên 32 và số GOAL PASS tăng từ 11 lên 31.

Kết quả này là bằng chứng về tính khả thi của pipeline end-to-end trên phần lớn scenario chẩn đoán có ngữ cảnh trong tập thử nghiệm: tạo lỗi, thu thập dữ liệu, kết luận có cấu trúc, chấm điểm và cleanup. Tuy nhiên, TSR này chỉ áp dụng cho cohort, topology và evaluator đã nêu; không phải tỷ lệ thành công chung cho mọi nhiệm vụ quản trị mạng.

### 4.5.3. Trả lời RQ2 – Chất lượng chẩn đoán

Ngày 02/11, RCA F1, Localization F1 và Fault Type F1 trung bình đều đạt 0,9688. Việc ba chỉ số bằng nhau cho thấy 31 trường hợp PASS đã khớp cả vị trí và loại lỗi; trường hợp còn lại không khớp Ground Truth. Detection trung bình cũng đạt 0,9688.

Run duy nhất không đạt là scenario `CE-1B incorrect uplink IPv4 address` (`benc-031126-3000000d`). Run có Evaluation nhưng RCA F1 bằng 0. Đây là lỗi chẩn đoán của Agent, không phải lỗi setup hoặc cleanup. Kết quả cho thấy nhóm `wrong_ip_address` vẫn khó hơn các nhóm có dấu hiệu trực tiếp như interface shutdown, MPLS bị tắt hoặc BGP neighbor bị shutdown. Để xác nhận sai địa chỉ IP, Agent phải đối chiếu địa chỉ của hai đầu liên kết với topology và subnet dự kiến; chỉ quan sát trạng thái interface hoặc route riêng lẻ chưa đủ.

### 4.5.4. Trả lời RQ3 – Tác động của bằng chứng và điều tra bổ sung

Từ ngày 28/10, workflow có khả năng quay lại node investigation khi Analyst xác định thiếu bằng chứng. Ngày 30/10 bổ sung diagnostic playbook và Evidence Coverage Gate; ngày 31/10 bổ sung Causal Evidence Gate; ngày 01/11 hoàn thiện matcher MPLS và OSPF. Trong các cohort sau thay đổi, số PASS được báo cáo tăng ở nhóm MPLS và OSPF area mismatch; đây là quan sát mô tả, không phải phép so sánh đối chứng.

Evidence Gate giúp ngăn finalize khi còn thiếu loại bằng chứng bắt buộc, nhưng coverage cao không bảo đảm RCA đúng. Coverage phản ánh hệ thống đã thu thập đủ nhóm dữ liệu; Analyst hoặc matcher vẫn phải suy luận đúng quan hệ nhân quả từ nội dung. Trường hợp wrong IP còn thất bại ngày 02/11 là minh chứng cho giới hạn này.

### 4.5.5. Trả lời RQ4 – Chi phí thực thi

Active Latency trung bình thấp nhất được ghi nhận ngày 30/10 là 27,44 giây; trung vị thấp nhất ngày 31/10 là 24,37 giây. Khi investigation được thực thi đầy đủ vào ngày 01/11, RCA F1 tăng nhưng latency trung bình tăng lên 42,44 giây. Ngày 02/11, latency giảm còn 35,95 giây trong khi RCA F1 tiếp tục tăng lên 0,9688.

Kết quả gợi ý một sự đánh đổi giữa lượng bằng chứng và thời gian xử lý trên các cohort đã ghi nhận; muốn kết luận cơ chế nào tạo ra đánh đổi cần chạy ablation trong cùng điều kiện. Việc bổ sung kiểm tra có mục tiêu làm tăng một số lượt tool, nhưng có thể giảm các lệnh dư thừa và hạn chế vòng điều tra không cần thiết. Interaction Turns ngày 02/11 là 4,69, thấp hơn baseline 6,40 nhưng cao hơn 4,19 của ngày 31/10.

## 4.6. Phân tích quá trình cải tiến

Bảng 4.6 tóm tắt thay đổi chính gắn với từng cohort. Ngày trong bảng là ngày logic của dữ liệu benchmark, không phải ngày commit.

| Cohort | Thay đổi chính | Tác động quan sát được |
| --- | --- | --- |
| 27/10 | Thiết lập baseline structured diagnosis và evaluator v4 | 11/32 PASS; còn run không được chấm và nhiều kết luận thiếu bằng chứng |
| 28/10 | Thêm vòng `analyze → investigate → analyze`, confidence và evidence gap | PASS tăng lên 14; Detection và Localization cải thiện |
| 29/10 | Dùng evaluator v5, taxonomy lỗi và cleanup có hậu kiểm | Giảm lỗi vận hành nhưng độ chính xác gần như không đổi |
| 30/10 | Thêm diagnostic playbook, Evidence Coverage Gate, parser Planner và sửa scenario P3 không hợp lệ | PASS tăng lên 20; latency và turns giảm đáng kể |
| 31/10 | Thêm Causal Evidence Gate và parser/matcher theo giao thức | PASS tăng lên 23; mức giảm false positive chưa được kiểm định riêng |
| 01/11 | Hoàn thiện matcher MPLS, OSPF area mismatch, candidate recovery và thực thi investigation READ | PASS tăng lên 29; latency tăng đồng thời với investigation |
| 02/11 | Điều chỉnh điều phối và xử lý trường hợp chẩn đoán còn thiếu | PASS tăng lên 31; chỉ còn một scenario wrong IP thất bại |

Xu hướng tăng không hoàn toàn đơn điệu ở mọi metric. Ngày 29/10, RCA F1 giảm nhẹ so với 28/10 do thay evaluator và taxonomy. Ngày 01/11, độ chính xác tăng mạnh nhưng latency cũng tăng. Vì nhiều thay đổi được triển khai giữa hai cohort, kết quả không cho phép tách riêng mức đóng góp của từng thay đổi. Thiết kế ablation test là cần thiết nếu muốn xác định tác động độc lập của playbook, Evidence Gate hoặc matcher.

### 4.6.1. Thiết kế ablation để kiểm chứng đóng góp từng cơ chế

Bảng 4.6a là **giao thức thực nghiệm đề xuất, chưa phải kết quả ablation đã được thực thi**. Mục tiêu là đo đóng góp độc lập của cơ chế điều tra và hậu kiểm bằng chứng, thay vì quy nguyên nhân từ các cohort thay đổi nhiều yếu tố.

| Biến thể | Chỉ thay đổi so với cấu hình đầy đủ | Kết quả cần đo |
| --- | --- | --- |
| A0 — Full | Giữ investigation loop, diagnostic playbook, Evidence Coverage Gate, Causal Evidence Gate và protocol matcher | Baseline kiểm soát |
| A1 — No investigation | Tắt vòng READ bổ sung | GOAL, RCA F1, Interaction Turns, Latency |
| A2 — No coverage gate | Tắt quyết định điều tra dựa trên Evidence Coverage | GOAL, RCA F1, Coverage |
| A3 — No causal gate | Không dùng hậu kiểm nhân quả trước khi chốt RCA | Precision, False Positive, GOAL |
| A4 — No matcher | Không dùng matcher MPLS/OSPF chuyên biệt | F1 theo nhóm lỗi, Latency |

Các biến thể **chưa có feature flag tương ứng trong phiên bản code hiện tại**; khi thực hiện phải tạo cấu hình/nhánh thực nghiệm có thể tái lập và kiểm tra rằng chỉ một thành phần khác biệt. Giữ cố định scenario IDs và snapshot, topology, model, prompt, evaluator, tham số timeout và nền commit, chạy tối thiểu 3–5 lượt cho mỗi scenario/biến thể theo thứ tự hoán đổi. Mỗi lượt cần precondition, injection, fault verification, cleanup hậu kiểm. Công bố số Run hợp lệ, lỗi setup, GOAL Pass Rate, TSR API, macro RCA F1, latency/turns, độ lệch chuẩn và khoảng tin cậy. Cho đến khi có các run này, RQ3 chỉ được trả lời ở mức **tương quan mô tả**, không được trình bày như kết quả ablation.

## 4.7. Đánh giá cấu hình, khắc phục và an toàn

### 4.7.1. Khả năng cấu hình và khắc phục

Hệ thống đã hiện thực đường đi kỹ thuật cho Operation WRITE: Configuration Agent sinh CLI, Configuration Orchestrator kiểm tra output, Approval Gate yêu cầu quyết định người dùng, Network Agent thực thi và hệ thống lưu command/output. Tuy nhiên, tập benchmark trong chương này đánh giá nhiệm vụ chẩn đoán; metric `REMEDIATION` được lưu với `NOT_APPLICABLE` và `was_attempted=false`.

Cleanup của Benchmark Engine chỉ phục hồi lỗi do kịch bản tiêm vào môi trường, không phải hành động khắc phục do Agent đề xuất. Vì vậy không được dùng số Run CLEANED để công bố Remediation Success Rate. Muốn đánh giá khắc phục, cần xây dựng scenario riêng có hậu điều kiện, cho Agent thực hiện WRITE sau approval và kiểm tra trạng thái mạng bằng phép đo độc lập.

### 4.7.2. Cơ chế an toàn

Các cơ chế an toàn đã triển khai gồm RBAC, session authentication, mã hóa credential, giới hạn thiết bị trong inventory, validation interface, phân tách Planner và Configuration Agent, Approval Gate cho WRITE, command hash, thời hạn phê duyệt, Activity Log, Device Action Log và Audit Log.

Đây là bằng chứng về thiết kế và kiểm thử chức năng, chưa phải Safety Score thực nghiệm. Metric `SAFETY` hiện ở trạng thái `NOT_APPLICABLE` vì chưa có bộ scenario đối kháng và scorer độc lập để xác định tỷ lệ lệnh nguy hiểm bị chặn. Do đó báo cáo không công bố một tỷ lệ an toàn định lượng.

**Bảng 4.7. Ma trận kiểm thử Approval Gate đối với Operation WRITE**

| Điều kiện | Unit test hiện có/được bổ sung | Kỳ vọng |
| --- | --- | --- |
| Chưa có approval | `test_write_mapping_waits_without_approved_request` | Không gọi NetworkTool, yêu cầu phê duyệt |
| APPROVED, snapshot và hash đúng | `test_write_mapping_runs_only_when_snapshot_and_hash_match` | Chỉ thực thi command đã duyệt |
| REJECTED hoặc EXPIRED | `test_write_mapping_denied_or_expired_approval_never_reaches_network_tool` | Chặn WRITE, mapping REJECTED |
| Commands khác snapshot | `test_write_mapping_rejects_changed_commands_after_approval` | Chặn WRITE, mapping FAILED |
| Hash bị sửa nhưng commands giữ nguyên | `test_write_mapping_rejects_tampered_hash_with_unchanged_commands` | Chặn WRITE, mapping FAILED |
| Quyết định đến sau hạn | `test_expired_approval_cannot_be_decided` | Không cho quyết định trên approval đã hết hạn |

Các bài test thuộc `tests/agents/test_execution_orchestrator.py` và `tests/domains/test_execution_activity_approval.py`. Bảng mô tả các **trường hợp kiểm thử được viết trong mã nguồn**, không phải kết quả chạy PASS trên commit báo cáo. Khi nộp cần kèm output `pytest` thực chạy, kiểm thử tích hợp phân quyền/HTTP và tập thử nghiệm hành vi nguy hiểm độc lập. Không dùng các unit test này để suy ra Safety Rate hoặc Remediation Success Rate định lượng.

### 4.7.3. Cleanup và tính toàn vẹn môi trường

Trong cohort ngày 02/11, cả 32 Run đều kết thúc ở trạng thái CLEANED. Điều này xác nhận Benchmark Engine đã thực hiện và ghi nhận cleanup cho toàn bộ cohort. Trạng thái CLEANED không thay đổi kết quả GOAL: Run chẩn đoán sai vẫn là FAIL dù môi trường đã được phục hồi thành công.

Hai cohort đầu mỗi cohort có 31/32 Run CLEANED tại thời điểm truy vấn, trong khi những cohort từ 29/10 đến 02/11 đạt 32/32. Kết quả cho thấy cơ chế cleanup được cải thiện, nhưng để đánh giá độ tin cậy đầy đủ vẫn cần lưu số lần retry và kết quả hậu kiểm chi tiết cho từng action.

## 4.8. Thảo luận và hạn chế

### 4.8.1. Ý nghĩa của kết quả

Kết quả ngày 02/11 chứng minh tính khả thi của hệ thống trong việc chẩn đoán có cấu trúc trên topology GNS3: 31 trong 32 scenario được xác định đúng cả vị trí và loại lỗi. Việc sử dụng structured diagnosis giúp đánh giá nghiêm ngặt hơn so với tìm từ khóa, vì dự đoán thừa, sai interface hoặc sai loại lỗi đều làm giảm Precision, Recall hoặc F1.

Sự cải thiện từ 34,38% PASS/Run lên 96,88% xuất hiện cùng thời kỳ bổ sung điều tra dựa trên playbook và bằng chứng; chưa thể quy riêng mức cải thiện cho những cơ chế này. Tuy nhiên, kết quả cũng cho thấy việc thu thập đủ evidence chưa giải quyết hoàn toàn các lỗi cần đối chiếu quan hệ giữa nhiều thiết bị, điển hình là wrong IP address.

### 4.8.2. Các nguy cơ ảnh hưởng độ tin cậy

Các hạn chế chính gồm:

- Mỗi scenario chỉ được chạy một lần trong mỗi cohort; chưa có trung bình và độ lệch chuẩn trên nhiều lần lặp cùng phiên bản, chưa chạy các biến thể ablation A0–A4.
- Các cohort sử dụng nhiều phiên bản evaluator và mã nguồn khác nhau, nên không thể xem đây là thí nghiệm kiểm soát chỉ thay đổi một biến.
- Toàn bộ scenario đều chứa sự cố; chưa có negative case để đo false positive trên mạng khỏe.
- Tập thử nghiệm chỉ dùng một topology và một họ thiết bị Cisco IOS; một số `initial_message` cung cấp sẵn thiết bị/interface hoặc giao thức nghi vấn nên kết quả là chẩn đoán có ngữ cảnh, không phải zero-hint discovery.
- Ground Truth do người xây dựng scenario định nghĩa và cần được chuyên gia mạng rà soát độc lập.
- LLM và dịch vụ mạng bên ngoài có thể gây biến thiên về kết quả và latency.
- Metadata phần cứng, model version, prompt version và commit SHA chưa được đóng băng đầy đủ trong từng Run.

Vì những giới hạn trên, các tỷ lệ trong chương này được xem là kết quả thực nghiệm nội bộ trên tập benchmark của đề tài, không phải tuyên bố hiệu năng tổng quát hoặc so sánh trực tiếp với NIKA, NETARENA hay NetConfArena.

### 4.8.3. Hướng hoàn thiện thực nghiệm

Để tăng độ tin cậy, mỗi scenario cần được chạy tối thiểu từ ba đến năm lần với cùng model, prompt, evaluator và commit. Báo cáo tiếp theo nên trình bày trung bình, độ lệch chuẩn và khoảng tin cậy; đồng thời thực hiện ablation test bằng cách bật/tắt playbook, Evidence Gate và matcher chuyên biệt.

Tập scenario cần bổ sung trạng thái mạng khỏe, lỗi kết hợp nhiều nguyên nhân, topology khác và thiết bị khác nhà sản xuất. Đối với nhóm wrong IP, cần thu thập địa chỉ của cả hai đầu link, prefix dự kiến và topology peer trong cùng một evidence object để tránh suy luận từ từng output rời rạc.

## 4.9. Khả năng tái lập và nguồn bằng chứng

Một kết quả có thể được truy vết theo chuỗi:

```text
Benchmark Scenario/version
→ Benchmark Run/scenario_snapshot
→ Conversation và source Message
→ Task, Operation, Activity và Execution
→ structured diagnosis
→ Task Evaluation
→ Task Evaluation Metrics
```

Bảng 4.8 chỉ ra vị trí mã nguồn và dữ liệu dùng để kiểm chứng.

| Nội dung | Vị trí kiểm chứng |
| --- | --- |
| Scenario, action và Ground Truth | `src/app/domains/benchmark/` và `docker/postgres/seed/` |
| Benchmark Run, injection và cleanup | `src/app/domains/benchmark/services/` |
| Workflow Multi-Agent | `src/app/agents/workflow.py` và `src/app/agents/orchestrator/` |
| Structured diagnosis | activity `ANALYSIS_COMPLETED` và Evaluation tương ứng |
| RCA scoring | `src/app/domains/benchmark/utils/structured_rca.py` |
| GOAL và metric | `src/app/domains/benchmark/utils/evaluation.py` |
| Active Latency | `src/app/domains/benchmark/utils/active_runtime.py` |
| TSR và thống kê Run | `src/app/domains/benchmark/utils/summary.py` |
| Định nghĩa metric | `docs/benchmark-metrics.md` |
| Dữ liệu thực nghiệm | `benchmark_runs`, `task_evaluations`, `task_evaluation_metrics` |

Lệnh runner sử dụng để chạy một cohort có dạng:

```bash
.venv/bin/python scripts/run_benchmark_scenarios.py \
  --date YYYY-MM-DD \
  --email "<seeded-account>" \
  --password "<password>" \
  --force \
  --cooldown-seconds 15
```

Thông tin xác thực không được ghi vào báo cáo hoặc log công khai. Khi xuất dữ liệu phục vụ nghiên cứu, cần loại bỏ credential, token và các trường nhạy cảm; giữ lại ID, version, timestamp, metric, expected/actual/evidence và trạng thái cleanup cần thiết cho việc kiểm chứng.

---

# CHƯƠNG 5. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

Chương này tổng hợp các kết quả đạt được của đề tài, đối chiếu kết quả thực nghiệm với mục tiêu nghiên cứu, chỉ ra những hạn chế còn tồn tại và đề xuất hướng phát triển tiếp theo. Các kết luận được giới hạn trong phạm vi hệ thống, topology GNS3 và bộ Benchmark Scenario đã trình bày ở Chương 4.

## 5.1. Kết quả đạt được

### 5.1.1. Kết quả về nghiên cứu và thiết kế hệ thống

Đề tài đã nghiên cứu và xây dựng một hệ thống Multi-Agent hỗ trợ quản trị mạng bằng ngôn ngữ tự nhiên. Thay vì để một mô hình ngôn ngữ thực hiện toàn bộ quá trình, hệ thống phân chia trách nhiệm thành các thành phần chuyên biệt:

- **Planner Agent** phân tích yêu cầu, xác định loại nhiệm vụ, tạo Operation, quan hệ phụ thuộc và ánh xạ thiết bị. Planner chỉ mô tả yêu cầu cấu hình, không trực tiếp sinh CLI WRITE.
- **Configuration Agent** chuyển `configuration_requirements` thành các lệnh CLI theo từng thiết bị và Operation WRITE. Kết quả phải vượt qua structured schema và kiểm tra interface trước khi được lưu.
- **Network Agent** sử dụng NetworkTool để thực thi lệnh READ hoặc WRITE trên thiết bị; Agent này không tự thay đổi kế hoạch và không tự suy diễn kết luận.
- **Analyst Agent** tổng hợp kết quả thực thi, đánh giá bằng chứng và tạo kết luận gồm trạng thái bất thường, nguyên nhân gốc, phát hiện chính và hành động đề xuất.
- **Orchestrator** điều phối vòng đời yêu cầu, gọi Agent phù hợp, kiểm tra trạng thái nghiệp vụ, thực hiện Approval Gate và quyết định khi nào cần điều tra bổ sung hoặc kết thúc workflow.

LangGraph được sử dụng để biểu diễn luồng xử lý qua các node `check_gns3`, `plan`, `configure`, `execute`, `analyze`, `investigate` và `finalize`. Nhánh `configure` chỉ được sử dụng khi kế hoạch có Operation WRITE; kế hoạch chỉ có READ được chuyển trực tiếp sang thực thi. Việc tổ chức bằng conditional edge giúp luồng xử lý phản ánh đúng loại yêu cầu và tránh gọi Configuration Agent không cần thiết.

Dữ liệu nghiệp vụ không phụ thuộc hoàn toàn vào workflow state. PostgreSQL lưu Conversation, Message, Task, Operation, dependency, ánh xạ thiết bị, Approval, Execution, Activity, Audit Log và Evaluation. Nhờ đó, hệ thống có thể truy vết từ yêu cầu ban đầu đến lệnh đã gửi, output thiết bị, quyết định phê duyệt và kết quả đánh giá cuối cùng.

### 5.1.2. Kết quả xây dựng các chức năng

Các nhóm chức năng chính đã được hiện thực gồm:

1. **Identity và phân quyền:** quản lý người dùng, session, access/refresh token, role, permission và kiểm tra quyền theo chức năng–hành động.
2. **Inventory:** quản lý Brand, Category, Device và Credential; thông tin bí mật được mã hóa khi lưu và chỉ giải mã trong lớp kết nối nội bộ.
3. **Conversation:** quản lý hội thoại, phân trang message, đổi tiêu đề và cung cấp tối đa năm message trước đó làm ngữ cảnh cho yêu cầu tiếp theo.
4. **Planning:** chuyển yêu cầu thành `ExecutionPlanCreate`, kiểm tra device/interface/dependency và chỉ vật hóa kế hoạch sau khi dữ liệu hợp lệ.
5. **Configuration:** sinh CLI riêng cho các Operation WRITE, loại bỏ lệnh quản lý phiên và kiểm tra CLI trước khi đưa sang giai đoạn thực thi.
6. **Execution:** thực thi DAG theo dependency, tổng hợp trạng thái Operation và Task, lưu Task Execution và Device Action Log.
7. **Human-in-the-loop:** tạo khung phê duyệt theo từng ánh xạ Operation–Device; hỗ trợ APPROVED, REJECTED và EXPIRED; kiểm tra command snapshot/hash trước khi chạy WRITE.
8. **Analysis và investigation:** tạo structured diagnosis, đánh giá Evidence Coverage/Causal Evidence và phát sinh kế hoạch READ bổ sung khi chưa đủ căn cứ.
9. **Workflow nền:** API đưa yêu cầu vào durable workflow job; Workflow Worker tiếp nhận và xử lý ngoài vòng đời request HTTP, giảm phụ thuộc vào `BackgroundTasks` trong tiến trình API.
10. **Cập nhật thời gian thực:** SSE phát lại activity đã lưu và nhận thông báo mới từ PostgreSQL để giao diện theo dõi tiến trình mà không phải liên tục tải lại toàn bộ Task.
11. **Benchmark Engine:** quản lý Scenario, precondition, injection, fault verification, Ground Truth, Run và cleanup; lưu snapshot scenario cho từng lượt chạy.
12. **Evaluation:** chấm GOAL, RCA, Detection, Localization, Fault Type, Latency và Interaction Turns; lưu expected, actual và evidence để kiểm tra lại kết quả.
13. **Audit và giám sát:** lưu Task Activity Event, Device Action Log và Audit Log, hỗ trợ tra cứu theo lịch sử nghiệp vụ.
14. **Frontend:** cung cấp giao diện Chat, Task, Approval, Dashboard, Device, Credential, Device Catalog, User, Access Control, Audit Log, Benchmark Scenario, Benchmark Run và Evaluation.

Các chức năng trên tạo thành một chuỗi xử lý hoàn chỉnh từ tiếp nhận yêu cầu, lập kế hoạch, thu thập dữ liệu, phê duyệt cấu hình, thực thi, phân tích đến đánh giá kết quả.

### 5.1.3. Kết quả thực nghiệm và trả lời câu hỏi nghiên cứu

Thực nghiệm gồm bảy cohort đầy đủ từ ngày logic 27/10 đến 02/11/2026, mỗi cohort có 32 scenario, tạo thành 224 Benchmark Run. Kết quả cuối cùng ngày 02/11 có đủ 32 Evaluation, trong đó 31 Run GOAL PASS và một Run GOAL FAIL.

**Đối với RQ1 – khả năng hoàn thành nhiệm vụ:** cohort ngày 02/11 đạt Task Success Rate 96,88%. So với baseline ngày 27/10 có 11/32 PASS, kết quả tăng lên 31/32 PASS, tương ứng tăng 62,50 điểm phần trăm trên toàn cohort. Kết quả chứng minh pipeline có thể hoàn thành phần lớn nhiệm vụ chẩn đoán trong tập benchmark nội bộ.

**Đối với RQ2 – chất lượng chẩn đoán:** RCA F1, Localization F1 và Fault Type F1 trung bình ngày 02/11 đều đạt 0,9688; Detection trung bình đạt 0,9688. Điều này cho thấy 31 scenario được xác định đúng cả tài nguyên và loại lỗi. Scenario còn thất bại thuộc nhóm `wrong_ip_address`, cho thấy việc suy luận lỗi địa chỉ giữa hai đầu liên kết vẫn cần bằng chứng topology và subnet chặt chẽ hơn.

**Đối với RQ3 – tác động của cơ chế bằng chứng:** kết quả tăng theo các cohort đồng thời với quá trình bổ sung investigation loop, diagnostic playbook, Evidence Coverage Gate, Causal Evidence Gate và matcher MPLS/OSPF. Các cơ chế này được thiết kế để ngăn finalize khi thiếu bằng chứng, nhưng dữ liệu cohort hiện chưa đo được đóng góp riêng của từng thành phần. Tuy nhiên, coverage đầy đủ không bảo đảm suy luận đúng nội dung; Evidence Gate là điều kiện kiểm soát dữ liệu đầu vào chứ không thay thế khả năng RCA của Analyst.

**Đối với RQ4 – chi phí thực thi:** active latency trung bình ngày 02/11 là 35,95 giây, trung vị 32,82 giây và Interaction Turns trung bình 4,69. So với baseline 6,40 tool calls, số lượt tương tác giảm dù chất lượng chẩn đoán tăng. Kết quả cũng cho thấy đánh đổi giữa độ chính xác và thời gian: khi investigation được thực thi đầy đủ ngày 01/11, latency tăng do hệ thống thu thập thêm bằng chứng.

**Đối với RQ5 – kiểm soát và khôi phục môi trường:** toàn bộ 32 Run ngày 02/11 kết thúc ở trạng thái CLEANED. Hệ thống đã hiện thực Approval Gate cho Operation WRITE và lưu dấu vết quyết định. Tuy nhiên, CLEANED chỉ xác nhận Benchmark Engine đã phục hồi môi trường, không phải bằng chứng Agent đã khắc phục sự cố thành công.

Kết quả trên cho phép kết luận hệ thống đáp ứng được mục tiêu xây dựng một nguyên mẫu Multi-Agent có khả năng chẩn đoán, tương tác với thiết bị GNS3, kiểm soát thay đổi cấu hình và đánh giá kết quả có cấu trúc. Các tỷ lệ chỉ có giá trị trong phạm vi tập benchmark của đề tài, không được khái quát thành hiệu năng trên mạng sản xuất.

### 5.1.4. Đóng góp của đề tài

Các đóng góp chính của đề tài gồm:

- Đề xuất và hiện thực kiến trúc Multi-Agent phân tách rõ lập kế hoạch, sinh cấu hình, thực thi và phân tích.
- Kết hợp LangGraph với trạng thái nghiệp vụ bền vững trong PostgreSQL, cho phép theo dõi và tiếp tục xử lý sau phê duyệt.
- Xây dựng cơ chế Human-in-the-loop theo từng thiết bị, giúp người quản trị kiểm soát các thao tác WRITE trước khi thực thi.
- Xây dựng Benchmark Engine tích hợp trực tiếp với GNS3 để kiểm tra precondition, tiêm lỗi, xác minh, chấm điểm và cleanup.
- Áp dụng structured diagnosis và phép đánh giá RCA dựa trên cặp tài nguyên–loại lỗi, khắc phục hạn chế của cách chấm từ khóa.
- Xây dựng cơ chế thu thập bằng chứng theo playbook và điều tra bổ sung có giới hạn.
- Cung cấp giao diện thống nhất để quản lý tài nguyên mạng, theo dõi hoạt động Agent, phê duyệt thay đổi và phân tích kết quả benchmark.

### 5.1.5. Đối chiếu mục tiêu nghiên cứu

| Mục tiêu | Kết quả thực hiện | Mức độ |
| --- | --- | --- |
| Nghiên cứu LLM, AI Agent, Multi-Agent và Network Automation | Đã tổng hợp cơ sở lý thuyết và các công trình liên quan | Hoàn thành |
| Thiết kế kiến trúc Multi-Agent | Đã xây dựng Planner, Configuration, Network, Analyst và Orchestrator | Hoàn thành |
| Tiếp nhận yêu cầu bằng ngôn ngữ tự nhiên | Đã tích hợp Chat, Conversation và LLM | Hoàn thành |
| Tương tác với thiết bị mạng | Đã tích hợp NetworkTool, Netmiko/Nornir và GNS3 | Hoàn thành trong lab |
| Kiểm soát thay đổi cấu hình | Đã có RBAC, Approval Gate, command hash và audit | Hoàn thành ở mức nguyên mẫu |
| Chẩn đoán và RCA | Đã có structured diagnosis, investigation và Evidence Gate | Hoàn thành trong phạm vi scenario |
| Xây dựng benchmark có Ground Truth | Đã có Scenario, Run, injection, verification, Evaluation và cleanup | Hoàn thành |
| Đánh giá TSR, Detection, Localization, RCA, Latency và Turns | Đã có metric, API, giao diện và dữ liệu thực nghiệm | Hoàn thành |
| Đánh giá Remediation Success Rate | Chưa có hậu kiểm độc lập sau thao tác sửa lỗi của Agent | Chưa hoàn thành |
| Đánh giá Safety định lượng | Đã có cơ chế phòng ngừa nhưng chưa có Safety Evaluator độc lập | Chưa hoàn thành |
| Thực nghiệm đa topology, đa model và nhiều lần lặp | Chưa thực hiện đủ để phân tích thống kê | Chưa hoàn thành |

## 5.2. Hạn chế của đề tài

### 5.2.1. Hạn chế về phạm vi môi trường mạng

Hệ thống mới được thực nghiệm trên một topology GNS3 và chủ yếu với Cisco IOS. Các driver và schema có thể hỗ trợ mở rộng, nhưng đề tài chưa chứng minh khả năng hoạt động tương đương trên thiết bị thật, topology lớn, nhiều vendor hoặc môi trường mạng có tải thực tế. Trạng thái mạng được quan sát chủ yếu qua CLI theo yêu cầu, chưa có telemetry liên tục từ SNMP, streaming telemetry hoặc hệ thống giám sát bên ngoài.

### 5.2.2. Hạn chế của Agent và mô hình ngôn ngữ

Planner Agent và Analyst Agent phụ thuộc vào chất lượng và độ sẵn sàng của LLM bên ngoài. Mặc dù hệ thống có schema validation, retry và timeout, mô hình vẫn có thể trả JSON sai, bỏ sót Operation hoặc diễn giải bằng chứng không chính xác. Matcher chuyên biệt cải thiện kết quả cho những nhóm lỗi đã biết nhưng có thể làm hệ thống phụ thuộc vào taxonomy và playbook được xây dựng trước.

Ngữ cảnh hội thoại hiện chỉ lấy một số message gần nhất, chưa có cơ chế bộ nhớ dài hạn, tóm tắt ngữ cảnh hoặc truy hồi tri thức theo từng mạng. Configuration Agent chưa được tích hợp kho tài liệu nhà sản xuất theo cơ chế RAG; vì vậy chất lượng CLI vẫn phụ thuộc vào prompt, inventory và kiến thức sẵn có của model.

### 5.2.3. Hạn chế trong cấu hình và khắc phục sự cố

Hệ thống có thể thực thi Operation WRITE sau phê duyệt nhưng chưa hình thành một vòng closed-loop remediation hoàn chỉnh cho toàn bộ loại lỗi. Chưa có cơ chế transaction hoặc rollback nguyên tử trên nhiều thiết bị; khi một phần cấu hình đa thiết bị thất bại, hệ thống chủ yếu ghi trạng thái và báo cáo thay vì tự động khôi phục toàn bộ thay đổi trước đó.

Configuration validation hiện tập trung vào schema, interface, thiết bị và một số quy tắc lệnh. Hệ thống chưa có mô hình kiểm chứng ngữ nghĩa để dự đoán ảnh hưởng của cấu hình đến toàn topology trước khi chạy. Việc người dùng phê duyệt cũng không tự động bảo đảm lệnh đúng về mặt thiết kế mạng.

### 5.2.4. Hạn chế của bộ benchmark và phương pháp đánh giá

Mỗi scenario chỉ được chạy một lần trong từng cohort. Các cohort thay đổi đồng thời mã nguồn, prompt và đôi khi evaluator version; do đó mức tăng kết quả chỉ thể hiện xu hướng của toàn pipeline, chưa chứng minh tác động độc lập của từng thành phần. Chưa có nhiều lần lặp để tính độ lệch chuẩn, khoảng tin cậy hoặc kiểm định ý nghĩa thống kê.

Tập scenario hiện chỉ gồm các trường hợp có lỗi, chưa có mạng khỏe để đo false positive. Ground Truth do nhóm xây dựng theo topology của đề tài và chưa được đánh giá liên chủ thể bởi nhiều chuyên gia. Các scenario chưa bao phủ lỗi đồng thời, lỗi dao động, lỗi hiệu năng, sự cố đa hop phức tạp và những trường hợp không thể kết luận từ dữ liệu hiện có.

Evaluator v4 và v5 không hoàn toàn tương đương do v5 bổ sung taxonomy và chuẩn hóa alias. Vì vậy không nên gộp toàn bộ lịch sử thành một tỷ lệ duy nhất để so sánh khoa học. Cohort ngày 02/11 đạt 96,88%, nhưng kết quả này không đủ để tuyên bố hệ thống vượt NIKA, NETARENA, NetConfArena hoặc một phương pháp khác khi chưa chạy trên cùng dataset và điều kiện.

### 5.2.5. Hạn chế về an toàn, hiệu năng và vận hành

RBAC, Approval Gate, mã hóa credential, command hash và Audit Log là các cơ chế an toàn phòng ngừa, nhưng đề tài chưa có Safety Evaluator và tập kiểm thử đối kháng để tạo Safety Score. Remediation và Safety hiện được đánh dấu `NOT_APPLICABLE` trong benchmark chẩn đoán.

Active Latency chưa được phân rã thành thời gian LLM, thời gian thiết bị, database và orchestration. Hệ thống chưa thực nghiệm tải đồng thời nhiều conversation hoặc nhiều Task trên topology lớn. Durable Workflow Worker và PostgreSQL notification cải thiện độ bền và khả năng cập nhật, nhưng chưa có benchmark throughput, cơ chế phân phối nhiều worker, backpressure hoặc hàng đợi chuyên dụng cho quy mô sản xuất.

## 5.3. Hướng phát triển

### 5.3.1. Hoàn thiện đánh giá thực nghiệm

Ưu tiên trước mắt là chuẩn hóa bộ thực nghiệm. Mỗi scenario cần chạy tối thiểu từ ba đến năm lần trên cùng commit, model, prompt và evaluator. Metadata của Run cần bổ sung commit SHA, model version, prompt version, network adapter, cấu hình tham số và thông tin môi trường. Kết quả phải báo cáo trung bình, trung vị, độ lệch chuẩn và khoảng tin cậy.

Cần bổ sung negative scenario với mạng khỏe, scenario có nhiều nguyên nhân đồng thời và scenario không đủ dữ liệu để kết luận. Ablation test nên được thực hiện bằng cách lần lượt tắt playbook, Evidence Gate, Causal Gate và matcher chuyên biệt để xác định đóng góp của từng cơ chế.

### 5.3.2. Hoàn thiện chẩn đoán và quản lý tri thức

Đối với lỗi `wrong_ip_address`, hệ thống cần mô hình hóa liên kết hai đầu, địa chỉ mong đợi, prefix và subnet thành evidence có cấu trúc. Topology nên được đồng bộ thành graph có khả năng truy vấn đa hop thay vì chỉ cung cấp danh sách neighbor cục bộ.

Có thể xây dựng kho tri thức bằng RAG từ tài liệu Cisco và các tài liệu nhà sản xuất được kiểm soát phiên bản. Configuration Agent và Analyst Agent chỉ truy hồi những tài liệu phù hợp với platform, OS version và tính năng đang xử lý; nguồn tài liệu được đính kèm vào evidence để tăng khả năng giải thích và giảm hallucination.

### 5.3.3. Phát triển closed-loop remediation

Benchmark cần bổ sung nhóm scenario khắc phục, trong đó Agent không chỉ chẩn đoán mà còn đề xuất và thực thi cấu hình sau phê duyệt. Một Remediation Evaluator độc lập phải kiểm tra hậu điều kiện mạng, khả năng kết nối và việc không làm hỏng các dịch vụ liên quan.

Đối với cấu hình nhiều thiết bị, cần phát triển cơ chế pre-check, tạo checkpoint, thực thi theo pha, post-check và rollback. Khi một thiết bị thất bại, hệ thống phải xác định có tiếp tục, dừng hay hoàn tác các thiết bị đã thay đổi dựa trên policy được định nghĩa trước.

### 5.3.4. Nâng cao an toàn và quản trị

Safety Evaluator cần đánh giá lệnh cấm, thao tác vượt phạm vi, thay đổi làm mất kết nối quản trị, rò rỉ secret và hành vi bỏ qua approval. Có thể bổ sung policy engine để kiểm tra cấu hình trước khi hiển thị cho người dùng và trước khi gửi đến NetworkTool.

Audit Log cần hỗ trợ retention policy, export, chữ ký hoặc cơ chế chống chỉnh sửa cho các môi trường yêu cầu kiểm toán cao. Credential nên được tích hợp với secret manager chuyên dụng khi triển khai ngoài phòng lab.

### 5.3.5. Nâng cao khả năng mở rộng và độ tin cậy

Workflow job có thể được chuyển sang message broker hoặc hàng đợi chuyên dụng khi cần nhiều worker và retry phân tán. Hệ thống cần bổ sung idempotency key, dead-letter queue, lease/heartbeat, backpressure và cơ chế phục hồi job bị gián đoạn.

Các truy vấn danh sách tiếp tục được chuẩn hóa theo server-side filtering, pagination và count trong cùng API. SSE có thể giữ vai trò cập nhật một chiều cho activity; WebSocket chỉ cần thiết nếu tương lai có tương tác hai chiều tần suất cao. Cần thực hiện load test cho API, SSE, Workflow Worker và database để xác định giới hạn thực tế.

### 5.3.6. Mở rộng phạm vi triển khai

Các thực nghiệm tiếp theo cần sử dụng nhiều topology, nhiều vendor và nhiều model. Việc so sánh với NIKA, NETARENA hoặc NetConfArena chỉ nên thực hiện khi hệ thống cùng chạy trên dataset, rubric và điều kiện tương đương. Ngoài GNS3, có thể tích hợp containerlab hoặc môi trường testbed vật lý để đánh giá khả năng chuyển giao từ mô phỏng sang thực tế.

## 5.4. Kết luận chung

Đề tài đã xây dựng được một hệ thống Multi-Agent có khả năng tiếp nhận yêu cầu quản trị mạng bằng ngôn ngữ tự nhiên, lập kế hoạch, sinh cấu hình, tương tác với thiết bị GNS3, phân tích kết quả và kiểm soát thao tác thay đổi bằng Human-in-the-loop. Việc phân tách Planner, Configuration, Network và Analyst Agent giúp xác định rõ trách nhiệm, giảm việc để LLM trực tiếp thực thi thao tác ngoài phạm vi và tăng khả năng kiểm tra từng giai đoạn.

Hệ thống không chỉ dừng ở giao diện hội thoại mà còn xây dựng các domain nghiệp vụ cho Identity, Inventory, Conversation, Execution, Benchmark, Evaluation và Audit. Dữ liệu được lưu có cấu trúc cho phép truy vết từ yêu cầu đến kết quả, trong khi Benchmark Engine cung cấp quy trình tiêm lỗi, xác minh, đánh giá và cleanup trên topology GNS3.

Kết quả thực nghiệm tốt nhất đạt 31/32 GOAL PASS, tương đương 96,88%, với RCA F1 trung bình 0,9688 trên cohort ngày 02/11/2026. So với baseline, GOAL PASS tăng cùng thời điểm bổ sung playbook, investigation loop và Evidence Gate; chưa có ablation giữ các yếu tố khác cố định để xác nhận quan hệ nhân quả. Tuy nhiên, do số lần lặp, phạm vi topology và điều kiện đánh giá còn giới hạn, kết quả chỉ chứng minh tính khả thi và hiệu quả trong môi trường thử nghiệm của đề tài.

Nhìn chung, đề tài xây dựng được nguyên mẫu Multi-Agent hỗ trợ cấu hình và chẩn đoán sự cố mạng có kiểm soát, có cơ chế đánh giá; kết quả được xác nhận trong phạm vi các kịch bản chẩn đoán có ngữ cảnh, chưa chứng minh closed-loop remediation hoặc Safety Rate định lượng. Kết quả tạo nền tảng cho các nghiên cứu tiếp theo về closed-loop remediation, quản trị mạng dựa trên bằng chứng và triển khai AI Agent an toàn trong môi trường mạng quy mô lớn hơn.

---

# TÀI LIỆU THAM KHẢO

[1] J. Hong, N. V. Tu, and J. W.-K. Hong, “A Comprehensive Survey on LLM-Based Network Management and Operations,” International Journal of Network Management, vol. 35, 2025.

[2] O. G. Lira, O. M. Caicedo, and N. L. S. da Fonseca, “Large Language Models for Zero Touch Network Configuration Management,” arXiv:2408.13298, 2024.

[3] Z. Wang, A. Cornacchia, A. Sacco, F. Galante, M. Canini, and D. Jiang, “A Network Arena for Benchmarking AI Agents on Network Troubleshooting,” arXiv:2512.16381, 2025.

[4] Y. Zhou et al., “NETARENA: Dynamic Benchmarks for AI Agents in Network Automation,” International Conference on Learning Representations (ICLR), 2026.

[5] C. Liu, X. Xie, X. Chen, and Y. Cui, “NetConfArena: An Executable Benchmark for LLM Agents in Closed-Loop Network Configuration,” arXiv:2608.23179, 2026.

[6] Y. Luo et al., “OpsAgent: An Evolving Multi-agent System for Incident Management in Microservices,” arXiv:2510.24145, 2026.

[7] L. Zhang et al., “A Survey of AIOps in the Era of Large Language Models,” arXiv:2507.12472, 2025.

[8] M. Bajpai, “Automating Troubleshooting Network Issues with AIOps and Machine Learning,” Journal of Artificial Intelligence & Cloud Computing, vol. 3, no. 1, 2024.

[9] W. X. Zhao et al., “A Survey of Large Language Models,” Frontiers of Computer Science, vol. 20, no. 12, Art. no. 2012627, 2026. https://doi.org/10.1007/s11704-026-60308-3

[10] A. Vaswani et al., “Attention Is All You Need,” Advances in Neural Information Processing Systems, vol. 30, pp. 5998–6008, 2017. https://papers.neurips.cc/paper/7181-attention-is-all-you-need

[11] Z. Ji et al., “Survey of Hallucination in Natural Language Generation,” ACM Computing Surveys, vol. 55, no. 12, Art. no. 248, pp. 1–38, 2023. https://doi.org/10.1145/3571730

[12] M. Wooldridge and N. R. Jennings, “Intelligent Agents: Theory and Practice,” The Knowledge Engineering Review, vol. 10, no. 2, pp. 115–152, 1995. https://doi.org/10.1017/S0269888900008122

[13] Z. Xi et al., “The Rise and Potential of Large Language Model Based Agents: A Survey,” Science China Information Sciences, vol. 68, Art. no. 121101, 2025. https://doi.org/10.1007/s11432-024-4222-0

[14] Q. Wu et al., “AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation,” Proceedings of the Conference on Language Modeling (COLM), 2024. https://arxiv.org/abs/2308.08155

[15] E. Coronado et al., “Zero Touch Management: A Survey of Network Automation Solutions for 5G and 6G Networks,” IEEE Communications Surveys & Tutorials, vol. 24, no. 4, pp. 2535–2578, 2022. https://doi.org/10.1109/COMST.2022.3212586

[16] G. Malewicz et al., “Pregel: A System for Large-Scale Graph Processing,” Proceedings of the 2010 ACM SIGMOD International Conference on Management of Data, pp. 135–146, 2010. https://doi.org/10.1145/1807167.1807184

[17] S. K. S. Sidhu and A. Sharma, “The Evolution of Network Management: From Manual Configurations to Intelligent Automation,” International Journal of Network Management, vol. 36, no. 1, Art. no. e70031, 2026. https://doi.org/10.1002/nem.70031

[18] M. M. Abdellatif, O. Desouki, and M. AbdelRaheem, “Performance Analysis of Network Automation Techniques for Dense IP Networks,” Scientific Reports, vol. 16, Art. no. 9532, 2026. https://doi.org/10.1038/s41598-026-40975-9

[19] SANDS Lab, “NIKA 0.2: Scoring Implementation, RootCause Model and Scoring Tests.” https://github.com/sands-lab/nika/blob/main/src/nika/evaluator/scoring.py ; https://github.com/sands-lab/nika/blob/main/src/nika/problems/rca/models.py ; https://github.com/sands-lab/nika/blob/main/tests/nika/evaluator/test_scoring.py

[20] Netmiko Project, “Netmiko API Documentation.” https://ktbyers.github.io/netmiko/docs/netmiko/

[21] Nornir Project, “Nornir 3.6.0 Documentation — Plugins and Runners.” https://nornir.readthedocs.io/en/v3.6.0/plugins/

[22] GNS3 Project, “GNS3 Architecture Documentation.” https://docs.gns3.com/docs/using-gns3/design/architecture

---

# PHỤ LỤC A. BẢNG ĐỐI CHIẾU MÃ NGUỒN ĐÃ TRIỂN KHAI

| Thành phần             | File/đường dẫn                                                       | Vai trò xác minh                                 |
| ---------------------- | -------------------------------------------------------------------- | ------------------------------------------------ |
| LangGraph              | `src/app/agents/workflow.py`                                         | Graph thống nhất với entry route theo state      |
| Planner Agent          | `src/app/agents/planner/`                                            | Sinh và validate execution plan                  |
| Execution Orchestrator | `src/app/agents/orchestrator/execution.py`, `execution_runtime/`     | Điều phối Task/Operation/Approval                |
| Network Agent          | `src/app/agents/network/`, `src/app/tools/network/`                  | Kết nối và thực thi qua Netmiko/Nornir           |
| Analyst Agent          | `src/app/agents/analyst/`, `src/app/agents/orchestrator/analysis.py` | Diễn giải kết quả, ghi diagnosis_submission      |
| Identity/RBAC          | `src/app/domains/identity/`                                          | User, session, token, roles/permissions          |
| Inventory              | `src/app/domains/inventory/`                                         | Brand, category, device, credential/provider     |
| Conversation           | `src/app/domains/conversation/`                                      | Message, conversation, title                     |
| Execution              | `src/app/domains/execution/`                                         | Task, dependency, approval, activity, action log |
| Audit                  | `src/app/domains/audit/`                                             | Audit Log và bộ lọc                              |
| Benchmark              | `src/app/domains/benchmark/`                                         | Scenario/Run, injection, verification, cleanup   |
| RCA scorer             | `src/app/domains/benchmark/utils/structured_rca.py`                  | Tính precision, recall, F1 theo NIKA 0.2         |
| Evaluation             | `src/app/domains/evaluation/`                                        | Metric, result/evidence và API lịch sử           |
| TSR/Latency            | `src/app/domains/benchmark/utils/summary.py`, `active_runtime.py`    | Tổng hợp run và thời gian workflow               |
| Migration              | `migrations/versions/`, `scripts/migrate.py`                         | Kiểm soát schema theo version                    |
| Frontend               | Repository `network-multi-agent-system-frontend/src/features/`       | UI Chat, Tasks, Devices, Benchmark, Evaluation   |

# PHỤ LỤC B. API VÀ QUY TRÌNH TRUY VẾT

Các endpoint tiêu biểu dùng prefix `/api/v1`:

| Mục đích                      | Đường dẫn                                       |
| ----------------------------- | ----------------------------------------------- |
| Bắt đầu Conversation          | `POST /conversations/messages`                  |
| Xem message trong hội thoại   | `GET /conversations/{conversation_id}/messages` |
| Chi tiết kế hoạch và log Task | `GET /tasks/{task_id}/records`                  |
| Timeline Task                 | `GET /tasks/{task_id}/activity-events`          |
| Scenario management           | `GET/POST /benchmarks/scenarios`                |
| Bắt đầu Benchmark Run         | `POST /benchmarks/runs`                         |
| Thống kê TSR toàn bộ lịch sử  | `GET /benchmarks/runs/summary`                  |
| Cleanup một run               | `POST /benchmarks/runs/{run_id}/cleanup`        |
| Xem Evaluation                | `GET /evaluations`                              |
| Xem metric từng Task          | `GET /evaluations/tasks/{task_id}`              |
| Tra cứu hệ thống Audit Log    | `GET /audit-logs/`                              |

Quan hệ quan trọng khi đọc Evidence:

```text
BenchmarkScenario (version + Ground Truth)
   → BenchmarkRun (scenario_snapshot)
   → Conversation / USER_REQUEST Message
   → Task / TaskActivityEvent (diagnosis_submission)
   → TaskEvaluation (evaluator_version)
   → TaskEvaluationMetric (expected_value / actual_value / evidence)
   → Evaluation UI và TSR summary
```

Trình tự này cho phép đối chiếu dự đoán với nhãn kịch bản và truy xem Agent đã sử dụng lệnh nào. Khi đưa dữ liệu vào báo cáo hoặc phụ lục không xuất password, token, secret, mã khóa hay thông tin xác thực thiết bị.

# PHỤ LỤC C. NHẬT KÝ XÁC NHẬN KẾT QUẢ

**C.1. Kiểm thử được xác nhận (03/11/2026).** Nhóm cung cấp output `pytest` với bốn tệp: `tests/domains/test_nika_style_rca.py`, `tests/domains/test_benchmark_observations.py`, `tests/domains/test_benchmark_service.py`, `tests/agents/test_analyst_agent.py`. Kết quả: **42 collected, 42 passed, 1 warning, 1.86 s**. Đây là bốn bộ test được chọn, không phải toàn bộ test suite.

**C.2. Lượt Benchmark v4.** Giao diện Evaluation nhóm cung cấp hiển thị `db-benchmark-v4`, GOAL/RCA PASS, RCA F1/Precision/Recall và Localization/Fault Type F1/Detection 100%, Latency workflow 22,40 s, Interaction Turns 4. Các mục expected/actual/evidence chưa mở rộng nên không kết luận thêm thông tin không nhìn thấy.

**C.3. Phiên bản và thuật ngữ.** v1–v3 chấm GOAL/RCA từ khóa; v4 chấm nhãn có cấu trúc. v2 Latency đo end-to-end gồm chờ phê duyệt; v3–v4 đo active workflow time. Chỉ số `rca_accuracy` trong triển khai này là alias của Recall. `Interaction Turns` là số lượt Agent gọi tool, không phải số lần người dùng nhắn tin.

**C.4. Trạng thái chưa chấm.** `Remediation` và `Safety` trong v4 = NOT_APPLICABLE. Điều này không đồng nghĩa Agent an toàn tuyệt đối, không đồng nghĩa Agent đã sửa lỗi thành công và cũng không phải giá trị 0%/100%.

---

_Các bằng chứng kiểm thử cụ thể của Phụ lục C được nhóm cung cấp ngày 03/11/2026; mã nguồn `develop` được đối chiếu bổ sung tại commit ngày 18–19/11/2026 như phần đầu báo cáo. Chưa chạy lại toàn bộ benchmark và test suite cho những commit mới._
