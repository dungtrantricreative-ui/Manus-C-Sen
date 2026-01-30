# 🏆 Manus-Củ-Sen (Advanced Edition)

**Manus-Củ-Sen** là một AI Agent mã nguồn mở thế hệ mới, được thiết kế để mang lại sức mạnh của "Universal Agent" với hiệu suất tối đa và chi phí vận hành cực thấp. 

Dựa trên triết lý của Manus gốc, phiên bản **Củ Sen** tích hợp thuật toán **Planner-Executor-Critic** độc quyền, cho phép AI tự lập kế hoạch, thực thi và tự sửa lỗi một cách độc lập.

---

## ✨ Điểm nổi bật (Key Features)

### 🧠 Củ Sen Engine (Multi-Agent Loop)
AI không chỉ hoạt động đơn lẻ mà mô phỏng quy trình của một đội ngũ chuyên gia:
- **Manager (Planner)**: Phân tích yêu cầu và lập "bản đồ thực thi" thông minh.
- **Executor**: Sử dụng bộ công cụ (Browser, Python, Search...) để hành động.
- **Critic (Verifier)**: Kiểm tra chéo kết quả sau mỗi bước. Nếu chưa đạt yêu cầu, AI sẽ tự động "quay xe" để sửa lỗi (Self-Correction).

### 🌐 Dual-Model Browser (Maverick Vision)
Hệ thống trình duyệt được tối ưu hóa vượt trội so với các bản OpenManus thông thường:
- **Sức mạnh kép**: Sử dụng mô hình tổng quát (GPT OSS 120B) để tư duy và mô hình thị giác chuyên biệt (**Llama-4-Maverick**) để điều khiển trình duyệt.
- **Vision-Assisted**: AI nhìn thấy ảnh chụp màn hình và DOM để click/type chính xác như người thật.
- **Cost-Efficient**: Tối ưu hóa dữ liệu gửi đi, giảm tới 70% chi phí token.

### 💻 Code Interpreter & Memory
- **Python REPL**: Viết và chạy code Python ngay lập tức để giải toán, vẽ biểu đồ hoặc xử lý dữ liệu nặng.
- **Persistent Memory**: Ghi nhớ sở thích người dùng và dữ liệu quan trọng qua nhiều phiên làm việc.

---

## 🚀 Hướng dẫn cài đặt nhanh (Quick Start)

### 1. Yêu cầu hệ thống
- Python 3.10 trở lên.
- API Key từ SambaNova hoặc Groq (Sử dụng Llama 4 Scout và Maverick).

### 2. Cài đặt môi trường
```powershell
# Clone dự án và truy cập thư mục
cd Manus-Cu-Sen

# Cài đặt các thư viện lõi
pip install -r requirements.txt

# Cài đặt trình duyệt tự động cho AI
python -m playwright install chromium
```

### 3. Cấu hình `config.toml`
Mở file `config.toml` và điền thông tin của bạn:
```toml
[llm]
gemini_api_key = "YOUR_SAMBANOVA_OR_GROQ_KEY"
model_name = "gpt-oss-120b"
vision_model_name = "llama-4-maverick-17b-128e-instruct"
base_url = "https://api.sambanova.ai/v1"

[tools]
tavily_api_key = "YOUR_TAVILY_KEY" # Tùy chọn để tăng sức mạnh tìm kiếm
```

### 4. Khởi động
```bash
python main.py
```

---

## 🛠️ Bộ công cụ (Toolbox)
- **Browser**: Lướt web, tương tác giao diện qua Maverick Vision.
- **Python REPL**: Thực thi mã Python an toàn.
- **Search & Scraper**: Tìm kiếm và trích xuất nội dung web sang Markdown.
- **File Ops**: Quản lý tệp tin trực tiếp trong workspace.
- **Persistent Memory**: Lưu trữ tri thức dài hạn.

---

## 🤝 Đóng góp
Chúng tôi luôn hoan nghênh các đóng góp để biến **Manus-Củ-Sen** trở thành Agent mạnh mẽ nhất và dễ tiếp cận nhất. Hãy Fork và gửi Pull Request!

---
*Phát triển bởi cộng đồng yêu AI - Tối ưu cho hiệu suất thực tế.*
