# Hướng dẫn sử dụng Manus-C-Sen ULTIMATE (Brain Transplant Edition)

## 1. Giới thiệu

Manus-C-Sen ULTIMATE là một tác nhân AI tự trị tiên tiến, được thiết kế để thực thi các tác vụ với độ chính xác cao và hiệu quả tối ưu. Dự án này đại diện cho một bước tiến đáng kể trong lĩnh vực AI tự trị, được biết đến với tên gọi "Brain Transplant" (Phase 11). Phiên bản này tích hợp sâu rộng logic cốt lõi từ dự án OpenManus, mang lại một nền tảng vững chắc cho các hoạt động phức tạp. Đặc biệt, nó được tăng cường với các biện pháp bảo mật môi trường nghiêm ngặt, một trình duyệt hỗ trợ thị giác tiên tiến, cơ chế nhắc nhở động (dynamic prompting) có khả năng thích ứng theo ngữ cảnh, và một hệ thống thực thi công cụ mạnh mẽ. Sự kết hợp này cho phép Manus-C-Sen ULTIMATE không chỉ hiểu và phản ứng với môi trường số một cách thông minh mà còn thực hiện các tác vụ đa dạng từ duyệt web, phân tích dữ liệu đến quản lý thông tin một cách tự động và đáng tin cậy.

Cách thức hoạt động của Manus-C-Sen ULTIMATE dựa trên một vòng lặp phản hồi liên tục, nơi tác nhân liên tục quan sát môi trường, suy nghĩ về hành động tiếp theo và thực thi các công cụ phù hợp. Với "đôi mắt" là trình duyệt hỗ trợ thị giác, tác nhân có thể thu thập thông tin trực quan từ các trang web, hiểu được cấu trúc và các phần tử tương tác. "Bộ não" của nó, được hỗ trợ bởi các mô hình ngôn ngữ lớn (LLM) và cơ chế nhắc nhở động, cho phép nó lập kế hoạch, suy luận và đưa ra quyết định một cách linh hoạt. Khi cần thực hiện một hành động, tác nhân sẽ chọn công cụ phù hợp từ bộ công cụ đa dạng của mình, từ việc thực thi mã Python đến chạy các lệnh shell hoặc tìm kiếm thông tin trên web. Mỗi hành động được thực hiện sẽ tạo ra một phản hồi, được tác nhân sử dụng để cập nhật trạng thái và điều chỉnh kế hoạch tiếp theo, tạo thành một chu trình tự cải tiến liên tục.

## 2. Các tính năng nổi bật

Manus-C-Sen ULTIMATE được trang bị một loạt các tính năng tiên tiến, giúp nó trở thành một công cụ mạnh mẽ cho các tác vụ tự động hóa:

Manus-C-Sen ULTIMATE được trang bị một loạt các tính năng tiên tiến, giúp nó trở thành một công cụ mạnh mẽ cho các tác vụ tự động hóa. Đầu tiên, **Trình duyệt hỗ trợ thị giác (`browser-use`)** cho phép tác nhân "nhìn" trang web thông qua ảnh chụp màn hình, phân tích các phần tử tương tác một cách trực quan và điều hướng các ứng dụng trang đơn (SPA) phức tạp như YouTube, Gmail hoặc các bảng điều khiển chứng khoán một cách dễ dàng, loại bỏ việc phải đoán các bộ chọn CSS một cách mù quáng.

Thứ hai, tính năng **Tiêm ngữ cảnh ("The Eyes")** đảm bảo rằng trước mỗi quyết định, tác nhân sẽ tiêm trạng thái trình duyệt hiện tại (URL, Tiêu đề, Ảnh chụp màn hình) trực tiếp vào quá trình suy nghĩ của nó. Điều này giúp tác nhân không bao giờ bị "lạc" hoặc quên tab nào đang mở. Cùng với đó, **Nhắc nhở động ("The Brain")** cho phép hệ thống nhắc nhở thích ứng theo thời gian thực. "Chế độ trình duyệt" được kích hoạt khi duyệt web, tập trung vào điều hướng trực quan, trong khi "Chế độ lập trình viên" được kích hoạt khi viết mã, tập trung vào cú pháp và logic.

Ngoài ra, tác nhân còn có khả năng **Thực thi Python trong Sandbox (`python_execute`)**. Công cụ `PythonTool` mới này cho phép tác nhân thực thi mã Python một cách an toàn cho các phép tính, phân tích dữ liệu và xác minh logic. Một **Bộ công cụ chính (`Master Tool Suite`)** toàn diện bao gồm các công cụ mạnh mẽ như `browser_use` để tương tác web, `python_execute` để thực thi mã Python, `terminal` để thực thi lệnh shell, `search_tool` để tìm kiếm thông tin thời gian thực và `scraper` để trích xuất nội dung từ URL.

Để đảm bảo tính liên tục và hiệu quả, Manus-C-Sen ULTIMATE tích hợp **Cơ chế dự phòng LLM**, cho phép tác nhân chuyển đổi linh hoạt giữa các nhà cung cấp LLM khác nhau (ví dụ: Sambanova, Groq, Cerebras) trong trường hợp nhà cung cấp chính gặp sự cố hoặc giới hạn tốc độ. Tính năng **Tối ưu hóa chi phí** được tích hợp thông qua cơ chế theo dõi mức sử dụng token và chi phí, cùng với bộ nhớ đệm phản hồi để giảm thiểu chi phí khi thực hiện các truy vấn lặp lại. Cuối cùng, **Bảo mật và làm cứng môi trường** được đảm bảo bởi `schema.py`, đóng vai trò là "Người bảo vệ", xác thực dữ liệu và làm sạch từng byte để bảo vệ tác nhân khỏi rò rỉ token, ngay cả với "bộ não" mới.

## 3. Kiến trúc nội bộ

Manus-C-Sen ULTIMATE hoạt động dựa trên vòng lặp "ToolCall" của OpenManus. Dưới đây là mô tả chi tiết về các module chính:

Manus-C-Sen ULTIMATE hoạt động dựa trên vòng lặp "ToolCall" của OpenManus, với các module chính được tổ chức rõ ràng. **`agent_core.py`** đóng vai trò là "bộ não" mới của tác nhân, triển khai tác nhân `ManusCompetition` và `BrowserContextHelper`, quản lý luồng suy nghĩ, hành động và tương tác với các công cụ.

**`tools/browser_use_tool.py`** là công cụ trình duyệt hỗ trợ thị giác được tùy chỉnh, cho phép tương tác nâng cao với các trang web. **`llm.py`** chịu trách nhiệm xử lý các client LLM, bao gồm cơ chế dự phòng và gọi công cụ, đồng thời tích hợp theo dõi mức sử dụng và bộ nhớ đệm để tối ưu hóa chi phí.

**`schema.py`** định nghĩa các cấu trúc dữ liệu chính như `Message`, `AgentState`, `ToolCall`, `Function` và `Memory`, đồng thời thực hiện xác thực và làm sạch dữ liệu để đảm bảo an toàn. **`config.py`** quản lý cấu hình của tác nhân, bao gồm cài đặt LLM, công cụ được bật, cài đặt bộ nhớ đệm, bộ nhớ và giám sát. Cuối cùng, **`prompts.py`** chứa các mẫu nhắc nhở tập trung, hỗ trợ suy luận theo chuỗi suy nghĩ (CoT) và độ phức tạp thích ứng, hướng dẫn tác nhân trong quá trình ra quyết định.

## 4. Bộ công cụ chính (Master Tool Suite)

Manus-C-Sen ULTIMATE sử dụng một bộ công cụ đa dạng để thực hiện các tác vụ khác nhau:

Manus-C-Sen ULTIMATE sử dụng một bộ công cụ đa dạng để thực hiện các tác vụ khác nhau, mỗi công cụ được thiết kế với mục đích và hướng dẫn sử dụng cụ thể:

**`browser_use` (Tiêu chuẩn mới)** là công cụ chính để tương tác với web thông qua thư viện `browser-use`. Nó cung cấp các khả năng toàn diện như `go_to_url` để điều hướng đến một URL cụ thể, `click_element` để nhấp vào các phần tử tương tác, `input_text` để nhập văn bản vào các trường, `scroll` để cuộn trang, `extract_content` để trích xuất nội dung và `switch_tab` để chuyển đổi giữa các tab trình duyệt. Công cụ này đặc biệt thông minh với khả năng tự động tìm các phần tử dựa trên mô tả trực quan, giúp tác nhân tương tác với các trang web phức tạp một cách hiệu quả. Hướng dẫn sử dụng nhấn mạnh việc luôn gọi `go_to_url` đầu tiên để thiết lập ngữ cảnh, sau đó phân tích ảnh chụp màn hình và danh sách phần tử được trả về để xác định `INDEX` phù hợp cho các hành động nhấp hoặc nhập. Điều quan trọng là phải luôn đợi trang tải hoàn tất giữa các hành động để đảm bảo tính chính xác và tránh lỗi.

**`python_execute` (Mới!)** là một công cụ mạnh mẽ được thiết kế để thực thi mã Python trong một tiến trình sandbox an toàn. Công cụ này lý tưởng cho một loạt các tác vụ bao gồm phân tích dữ liệu phức tạp, thực hiện các phép tính toán học chính xác, thao tác chuỗi hiệu quả và xác minh logic chương trình. Một điểm quan trọng cần lưu ý là chỉ đầu ra được in ra console mới được ghi lại và trả về. Môi trường thực thi là sandbox, cho phép nhập các thư viện Python tiêu chuẩn nhưng có thể hạn chế quyền truy cập mạng bên ngoài để đảm bảo an toàn. Do đó, công cụ này đặc biệt hữu ích cho các tác vụ đòi hỏi xử lý dữ liệu chuyên sâu hoặc các phép tính phức tạp mà ngôn ngữ tự nhiên khó có thể diễn đạt hoặc thực hiện.

**`terminal` (Tích hợp hệ thống)** là một công cụ linh hoạt cho phép tác nhân thực thi các lệnh shell gốc, cung cấp khả năng chạy hầu hết mọi lệnh hệ thống như Python, pip, git, curl, hoặc PowerShell. Công cụ này đặc biệt hữu ích cho việc cài đặt gói phần mềm, quản lý tệp và là một công cụ dự phòng đáng tin cậy khi các công cụ chuyên biệt khác gặp sự cố. Hướng dẫn sử dụng nhấn mạnh việc luôn sử dụng các cờ không tương tác hoặc tự động chấp nhận (ví dụ: `winget install --accept-package-agreements`, `choco install -y`, `pip install --quiet`) để tránh các yêu cầu xác nhận thủ công. Đối với các tác vụ liên quan đến đa phương tiện, tác nhân được chỉ dẫn sử dụng `yt-dlp` cho tất cả các lượt tải xuống video và `ffmpeg` cho tất cả các chuyển đổi phương tiện. Trên hệ điều hành Windows, việc ưu tiên cú pháp PowerShell là bắt buộc để đảm bảo khả năng tương thích và hiệu quả tối ưu.

**`search_tool` (Thông tin thời gian thực)** là công cụ thiết yếu để thực hiện tìm kiếm trên web và đóng vai trò là giao diện chính để tác nhân truy cập kiến thức bên ngoài. Để tối ưu hóa hiệu quả tìm kiếm, nếu một truy vấn ban đầu thất bại, người dùng nên đơn giản hóa nó và tập trung vào việc sử dụng các từ khóa cụ thể thay vì các câu hỏi ngôn ngữ tự nhiên dài dòng. Công cụ này được thiết kế để tự động thử nhiều nhà cung cấp tìm kiếm khác nhau theo thứ tự ưu tiên (Tavily -> DuckDuckGo -> Google) để đảm bảo kết quả toàn diện nhất. Sau khi nhận được kết quả tìm kiếm, bước tiếp theo được khuyến nghị là sử dụng công cụ `scraper` trên các URL có triển vọng nhất để trích xuất thông tin chi tiết.

**`scraper` (Trích xuất nội dung web)** là một công cụ chuyên biệt được thiết kế để trích xuất nội dung văn bản sạch, dễ đọc từ một URL cụ thể. Nó sử dụng các kỹ thuật phân tích cú pháp nâng cao để loại bỏ các phần tử không cần thiết như quảng cáo, menu điều hướng và các thành phần giao diện người dùng khác, chỉ giữ lại nội dung cốt lõi. Công cụ này nên được sử dụng một cách có chọn lọc cho các URL đã được xác minh và có giá trị cao được tìm thấy thông qua công cụ tìm kiếm. Để tăng cường độ tin cậy, `scraper` sẽ tự động thử lại với các tiêu đề HTTP khác nhau trong trường hợp gặp lỗi ban đầu, giúp vượt qua một số cơ chế chống bot cơ bản.

**`file_ops` (Thao tác tệp)** là công cụ cung cấp các chức năng cơ bản nhưng thiết yếu để tương tác với hệ thống tệp. Nó cho phép tác nhân thực hiện các thao tác như đọc nội dung của một tệp, ghi dữ liệu vào một tệp (tạo mới hoặc ghi đè) và liệt kê các tệp hoặc thư mục trong một đường dẫn cụ thể. Công cụ này hỗ trợ sử dụng đường dẫn tuyệt đối, mang lại sự linh hoạt trong việc quản lý tài nguyên trên hệ thống.

Cuối cùng, **`knowledge` (Cơ sở kiến thức)** là một công cụ quan trọng, hoạt động như một cơ sở kiến thức cục bộ cho tác nhân. Mục đích chính của nó là lưu trữ và truy xuất các giải pháp thành công, các bài học kinh nghiệm hoặc thông tin chi tiết kỹ thuật đã được thu thập trong quá trình hoạt động. Việc này giúp tác nhân tiết kiệm token bằng cách tránh phải tìm kiếm lại thông tin đã biết và giải quyết các tác vụ lặp lại nhanh hơn. Công cụ này hỗ trợ ba lệnh chính: `save` để lưu một mục kiến thức mới với chủ đề và nội dung cụ thể; `search` để tìm kiếm các mục kiến thức hiện có dựa trên các từ khóa trong chủ đề; và `list` để hiển thị tất cả các chủ đề kiến thức hiện có trong cơ sở dữ liệu.

## 5. Cài đặt và cấu hình

Để thiết lập và chạy Manus-C-Sen ULTIMATE, hãy làm theo các bước sau:

### 5.1. Biến môi trường

Để cấu hình các biến môi trường cần thiết, người dùng cần sao chép tệp `.env.example` thành `.env` và điền các khóa API tương ứng. Việc này đảm bảo rằng tác nhân có thể truy cập các dịch vụ LLM và công cụ tìm kiếm (ví dụ: Tavily) một cách chính xác.

### 5.2. Cài đặt Dependencies

Quá trình cài đặt các gói phụ thuộc bao gồm việc sử dụng `pip` để cài đặt các thư viện Python được liệt kê trong `requirements.txt` và cài đặt trình duyệt Playwright. Các lệnh cần thực hiện là:

```shell
pip install -r requirements.txt
playwright install
```

### 5.3. Chạy tác nhân

Sau khi hoàn tất cài đặt, tác nhân có thể được khởi chạy bằng cách thực thi tệp `main.py`:

```shell
python main.py
```

Khi tác nhân khởi động thành công, người dùng sẽ thấy biểu ngữ "Manus-Củ-Sen ULTIMATE" và tác nhân sẽ sẵn sàng nhận lệnh.

## 6. Khắc phục sự cố

Trong quá trình sử dụng Manus-C-Sen ULTIMATE, người dùng có thể gặp một số vấn đề. Dưới đây là các câu hỏi thường gặp và cách khắc phục:

**Q: Lỗi "NameError: name 'List' is not defined"?**

**A**: Lỗi này đã được khắc phục trong bản cập nhật mới nhất của `base_tool.py`. Người dùng nên đảm bảo rằng họ đang sử dụng phiên bản mã nguồn mới nhất.

**Q: Trình duyệt không mở?**

**A**: Để khắc phục vấn đề này, hãy đảm bảo rằng bạn đã chạy lệnh `playwright install`. Công cụ `browser-use` được thiết kế để khởi chạy trình duyệt có giao diện người dùng theo mặc định, cho phép người dùng quan sát các hành động của tác nhân.

**Q: Lỗi 400 Bad Request?**

**A**: Lỗi này thường liên quan đến lớp "Absolute Sanitization" (Phase 10) của tác nhân, một tính năng bảo mật chủ động. Lớp này hoạt động để bảo vệ tác nhân khỏi rò rỉ token, ngay cả với "bộ não" mới. Nếu gặp lỗi này, hãy kiểm tra lại cấu hình và đảm bảo rằng không có dữ liệu nhạy cảm nào đang được truyền đi một cách không an toàn.

## 7. Kết luận

Manus-C-Sen ULTIMATE là một bước tiến đáng kể trong lĩnh vực tác nhân AI tự trị, mang lại khả năng tương tác web mạnh mẽ, thực thi mã linh hoạt và cơ chế suy luận thông minh. Với kiến trúc mô-đun và bộ công cụ đa dạng, nó có thể giải quyết nhiều loại tác vụ phức tạp, từ duyệt web đến phân tích dữ liệu và quản lý kiến thức. Việc hiểu rõ các tính năng và cách cấu hình sẽ giúp bạn tận dụng tối đa sức mạnh của tác nhân này.

---

_"Manus-Củ-Sen: Now with the Brain of OpenManus and the Heart of Steel."_

## 8. Các phương pháp hay nhất khi sử dụng Manus-C-Sen ULTIMATE

Để tối đa hóa hiệu quả và tránh các vấn đề không mong muốn khi làm việc với Manus-C-Sen ULTIMATE, hãy tuân thủ các phương pháp hay nhất sau:

Để tối đa hóa hiệu quả và tránh các vấn đề không mong muốn khi làm việc với Manus-C-Sen ULTIMATE, người dùng nên tuân thủ một số phương pháp hay nhất. Trước hết, cần **rõ ràng và cụ thể trong yêu cầu**, cung cấp các yêu cầu không mơ hồ để tác nhân có thể hoạt động tốt nhất. Việc **kiểm tra và xác minh kết quả** đầu ra của tác nhân là rất quan trọng, đặc biệt đối với các tác vụ quan trọng, nhằm đảm bảo tính chính xác và phù hợp với mục tiêu ban đầu.

Khi sử dụng `search_tool`, hãy **tối ưu hóa truy vấn tìm kiếm** bằng cách tập trung vào các từ khóa chính và cụm từ ngắn gọn thay vì các câu hỏi dài, giúp công cụ tìm kiếm trả về kết quả chính xác và liên quan hơn. Tương tự, **sử dụng `scraper` một cách có chọn lọc** trên các URL đã được xác minh để tránh các vấn đề về độ tin cậy hoặc pháp lý.

**Quản lý biến môi trường cẩn thận** là điều cần thiết; đảm bảo rằng các khóa API và thông tin nhạy cảm khác được lưu trữ an toàn trong tệp `.env` và không được đưa vào kiểm soát phiên bản. Người dùng cũng nên **theo dõi mức sử dụng và chi phí** thông qua tính năng của `llm.py` để quản lý ngân sách và tối ưu hóa việc sử dụng tài nguyên LLM. Cuối cùng, **tận dụng cơ sở kiến thức (`knowledge`)** bằng cách lưu trữ các giải pháp và thông tin hữu ích để tiết kiệm token và tăng tốc độ giải quyết các tác vụ lặp lại. Đồng thời, cần **hiểu rõ giới hạn của sandbox** khi sử dụng `python_execute` và `terminal`, vì các hoạt động mạng bên ngoài có thể bị hạn chế và một số lệnh hệ thống có thể không hoạt động như mong đợi.

## 9. Phát triển và cải tiến trong tương lai

Dự án Manus-C-Sen ULTIMATE không ngừng được phát triển và cải tiến. Một số hướng phát triển tiềm năng trong tương lai bao gồm:

Dự án Manus-C-Sen ULTIMATE không ngừng được phát triển và cải tiến, với nhiều hướng đi tiềm năng trong tương lai. Một trong những trọng tâm chính là **tăng cường khả năng học hỏi liên tục**, thông qua việc phát triển các cơ chế cho phép tác nhân học hỏi và thích nghi tốt hơn với các tác vụ mới và môi trường thay đổi, có thể thông qua học tăng cường hoặc các kỹ thuật học máy tiên tiến khác.

Bên cạnh đó, việc **mở rộng bộ công cụ** là một ưu tiên để tích hợp thêm các công cụ chuyên biệt cho các lĩnh vực cụ thể, chẳng hạn như công cụ phân tích tài chính, công cụ thiết kế đồ họa hoặc công cụ quản lý dự án, nhằm mở rộng đáng kể phạm vi ứng dụng của tác nhân. **Cải thiện khả năng tương tác người-AI** cũng là một mục tiêu quan trọng, thông qua việc phát triển giao diện người dùng trực quan hơn và các phương thức tương tác tự nhiên hơn, giúp người dùng dễ dàng hướng dẫn và cộng tác với tác nhân.

Để đảm bảo sự bền vững và hiệu quả, dự án sẽ tiếp tục **tối ưu hóa hiệu suất và chi phí** bằng cách tinh chỉnh các thuật toán và cơ chế nhằm giảm thiểu mức tiêu thụ tài nguyên (token, CPU, bộ nhớ) mà vẫn duy trì hoặc cải thiện hiệu suất tổng thể. Đồng thời, **tăng cường khả năng tự phục hồi** là một hướng phát triển quan trọng, cho phép tác nhân tự động phát hiện, chẩn đoán và khắc phục các lỗi hoặc sự cố trong quá trình hoạt động, từ đó giảm thiểu sự can thiệp của con người. Cuối cùng, việc **hỗ trợ đa ngôn ngữ nâng cao** sẽ được chú trọng; mặc dù hiện tại đã hỗ trợ tiếng Việt, việc cải thiện khả năng hiểu và tạo ra nội dung chất lượng cao bằng nhiều ngôn ngữ khác sẽ mở rộng đáng kể đối tượng người dùng và tiềm năng ứng dụng của Manus-C-Sen ULTIMATE.

Với những cải tiến liên tục, Manus-C-Sen ULTIMATE hứa hẹn sẽ trở thành một trợ lý AI ngày càng mạnh mẽ và linh hoạt, có khả năng giải quyết các thách thức phức tạp trong nhiều lĩnh vực khác nhau.
