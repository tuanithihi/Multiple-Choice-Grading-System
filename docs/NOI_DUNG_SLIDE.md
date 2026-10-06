# DÀN Ý SLIDE THUYẾT TRÌNH BẢO VỆ ĐỀ TÀI
## ĐỀ TÀI 19: HỆ THỐNG CHẤM PHIẾU TRẢ LỜI TRẮC NGHIỆM TỰ ĐỘNG TỪ ẢNH CHỤP (50 CÂU THPT)

---

### SLIDE 1: TRANG TIÊU ĐỀ (TITLE SLIDE)
- **Tiêu đề**: HỆ THỐNG CHẤM PHIẾU TRẮC NGHIỆM TỰ ĐỘNG TỪ ẢNH CHỤP (OMR 50 CÂU)
- **Học phần**: Thị giác máy tính (Computer Vision)
- **Nhóm sinh viên thực hiện**: Nhóm 19 (4 thành viên)
  1. Nguyễn Văn A (Nhóm trưởng)
  2. Trần Thị B
  3. Lê Văn C
  4. Phạm Thị D
- **Giảng viên hướng dẫn**: [Họ và tên giảng viên]
- **Gợi ý hình minh họa**: Logo trường, hình ảnh phiếu trắc nghiệm 50 câu và biểu tượng thị giác máy tính.

---

### SLIDE 2: ĐẶT VẤN ĐỀ & BÀI TOÁN NGHIỆP VỤ
- **Bất cập thực tế**: Chấm tay tốn thời gian, dễ nhầm lẫn; Máy chấm chuyên dụng đắt đỏ, đòi hỏi giấy phẳng và bảo trì phức tạp.
- **Mục tiêu đề tài**: Chấm thi nhanh chóng bằng điện thoại/webcam cá nhân, độ chính xác cao, chi phí 0 đồng.
- **Nghiệp vụ giáo viên chuẩn**:
  + Nguồn đáp án mẫu: Đọc trực tiếp từ ảnh phiếu giáo viên đã tô (không nhập tay thủ công).
  + Chấm bài học sinh: Ghép đúng mã đề, so sánh từng câu, phát hiện nghi ngờ và xuất bảng điểm.
- **Gợi ý hình minh họa**: Sơ đồ so sánh Máy quét đắt tiền vs Điện thoại chụp ảnh phiếu thi.

---

### SLIDE 3: TỔNG QUAN GIẢI PHÁP & LỰA CHỌN CÔNG NGHỆ
- **So sánh 3 hướng tiếp cận**:
  + Máy quét OMR chuyên dụng: Đắt đỏ, kém linh hoạt.
  + Học sâu (Deep Learning / YOLO): Nặng nề, cần GPU, khó giải thích lỗi sai.
  + Thị giác máy tính cổ điển + 4 Marker định vị: Tối ưu nhất (chạy CPU nhẹ, tốc độ cao, minh bạch 100%).
- **Công nghệ sử dụng**: Python 3.12, OpenCV 4, NumPy, Pandas, OpenPyXL, Pillow, Tkinter.
- **Gợi ý hình minh họa**: Bảng ma trận so sánh các tiêu chí (Tốc độ, Phần cứng, Tính minh bạch, Chi phí).

---

### SLIDE 4: QUY TRÌNH XỬ LÝ TỔNG THỂ (PIPELINE ARCHITECTURE)
- **Quy trình 5 bước liền mạch**:
  1. Tiền xử lý & Cân bằng sáng: Khử nhiễu Bilateral, ước lượng nền loại bỏ bóng đổ, CLAHE.
  2. Định vị phiếu & Nắn phối cảnh: Tìm 4 marker vuông đen $\to$ `warpPerspective` $\to$ Tự xoay 180°.
  3. Trích xuất ô tròn: Cắt lưới theo config, mặt nạ tròn nội tiếp triệt tiêu viền in.
  4. Nhận diện SBD, Mã đề & 50 câu: Phân tích Fill Ratio $\to$ Quyết định đáp án (HOP_LE, BLANK, MULTI, AMBIGUOUS).
  5. Chấm điểm & Báo cáo: So khớp mã đề $\to$ Tính điểm $\to$ Giao diện Tkinter, Excel, SQLite.
- **Gợi ý hình minh họa**: Sơ đồ khối pipeline 5 bước dạng flowchart trực quan.

---

### SLIDE 5: TIỀN XỬ LÝ & NẮN PHỐI CẢNH (WARP PERSPECTIVE)
- **Chiến lược phát hiện 2 lớp**:
  + Lớp 1 (Ưu tiên): Tìm 4 ô vuông đen (Marker) ở 4 góc bằng hình thái học và đặc trưng diện tích/tỉ lệ.
  + Lớp 2 (Dự phòng): Tìm tứ giác viền giấy trắng trên nền bàn (Canny + `approxPolyDP`).
- **Nắn phẳng chuẩn kích thước**: Đưa ảnh về chuẩn $1055 \times 1491$ pixel.
- **Tự động sửa chiều xoay 180°**:
  + Nhận diện vị trí cột marker phụ tại nửa trên phiếu ($x \sim 720\text{ px}$).
  + Tự động xoay $180^\circ$ nếu người dùng chụp ngược.
- **Gợi ý hình minh họa**: Hình ảnh phiếu gốc bị nghiêng/ngược bên cạnh ảnh sau khi nắn thẳng chuẩn kích thước.

---

### SLIDE 6: ĐỌC Ô TÔ TRẮC NGHIỆM (BUBBLE RECOGNITION)
- **Phân ngưỡng thích nghi cục bộ (Adaptive Threshold)**: Xử lý từng vùng $41 \times 41\text{ px}$, không bị ảnh hưởng bởi bóng đổ.
- **Mặt nạ tròn nội tiếp (Circular Mask)**:
  + Bán kính mặt nạ $R = 8\text{ px}$ (nằm lọt trong lòng ô tròn in sẵn $R_{\text{in}} \approx 11\text{ px}$).
  + Triệt tiêu $100\%$ nhiễu viền mực in sẵn.
- **Tính toán Tỉ lệ lấp đầy (Fill Ratio)**:
  + $\text{fill\_ratio} = \frac{\text{Số pixel trắng trong mặt nạ}}{\text{Diện tích mặt nạ (197 px)}}$.
- **Gợi ý hình minh họa**: Hình zoom cận cảnh 1 ô tròn: viền in sẵn, mặt nạ tròn màu đỏ và các pixel nét chì nhị phân.

---

### SLIDE 7: LOGIC QUYẾT ĐỊNH ĐÁP ÁN & NHẬN DIỆN THÔNG TIN
- **Phân loại đáp án 50 câu**:
  + $\ge 2$ ô có fill_ratio $\ge 0.38 \to \mathbf{MULTI}$ (Tô nhiều ô, 0 điểm).
  + Cả 4 ô $< 0.24 \to \mathbf{BLANK}$ (Bỏ trống, 0 điểm).
  + Ô cao nhất $\ge 0.38$ và chênh lệch $\ge 0.10 \to \mathbf{H\text{Ợ}P\_L\text{Ệ}}$ (chọn A/B/C/D).
  + Vùng mờ $[0.24, 0.38)$ hoặc chênh lệch hẹp $\to \mathbf{AMBIGUOUS}$ (Nghi ngờ tẩy không sạch).
- **Đọc SBD (4 chữ số) và Mã đề (3 chữ số)**:
  + Quét từng cột từ 0 đến 9, chọn hàng có fill_ratio cao nhất. Báo lỗi `?` nếu cột bỏ trống hoặc tô nhiều.
- **Gợi ý hình minh họa**: Biểu đồ cột thể hiện fill_ratio của 4 lựa chọn A, B, C, D cho từng trường hợp.

---

### SLIDE 8: DỰNG ĐÁP ÁN CHUẨN & CHẤM ĐIỂM TỰ ĐỘNG
- **Dựng đáp án chuẩn từ ảnh mẫu**:
  + Quét thư mục ảnh mẫu, dùng chung 1 pipeline đọc phiếu để lấy Mã đề và 50 đáp án.
  + Kiểm định chất lượng: Mã đề không được chứa `?`, cả 50 câu phải đủ A/B/C/D hợp lệ.
- **So khớp và Chấm điểm**:
  + Ghép bài làm học sinh với đáp án chuẩn CÙNG MÃ ĐỀ.
  + Công thức: $\text{Điểm} = \text{Số câu đúng} \times 0.20$.
  + Tự động phát hiện và cảnh báo **Nghi trùng bài** (cùng SBD và Mã đề).
- **Gợi ý hình minh họa**: Sơ đồ ghép mã đề giữa ảnh mẫu GV và bài làm HS, kèm bảng chấm điểm mẫu.

---

### SLIDE 9: GIAO DIỆN NGƯỜI DÙNG TKINTER ĐA LUỒNG
- **Quy trình 3 bước trực quan**:
  + Bước 1: Nạp ảnh/thư mục đáp án mẫu $\to$ Xem bảng đáp án chuẩn $\to$ Cho phép xác nhận/sửa tay.
  + Bước 2: Nạp bài làm học sinh (ảnh lẻ, thư mục, hoặc chụp trực tiếp từ webcam).
  + Bước 3: Bắt đầu chấm $\to$ Xem ảnh kép (ảnh gốc vs ảnh khoanh màu kết quả: Xanh/Đỏ/Vàng) $\to$ Sửa tay trực tiếp $\to$ Xuất Excel/SQLite.
- **Kiến trúc đa luồng (`threading.Thread(daemon=True)`)**:
  + Chấm hàng loạt không bị đơ giao diện; hiển thị thanh tiến trình thời gian thực.
  + Tự động cập nhật điểm số tức thì khi giáo viên sửa câu nghi ngờ.
- **Gợi ý hình minh họa**: Ảnh chụp thực tế giao diện hệ thống (`outputs/screenshots/gui_sample.png`).

---

### SLIDE 10: KẾT QUẢ THỰC NGHIỆM & ĐỘ BỀN HỆ THỐNG
- **Thử nghiệm trên 64 phiếu học sinh biến dạng nặng**:
  + Độ chính xác đọc từng câu: **99.38% (3180/3200 câu)** (chuẩn $\ge 97\%$).
  + Độ chính xác nhận diện SBD & Mã đề: **100% (64/64 phiếu)**.
  + Tỉ lệ crash chương trình: **0.0% (0/64 phiếu)**.
  + Tốc độ xử lý: **0.157 giây/phiếu** (Nhanh gấp 20 lần yêu cầu $\le 3\text{ giây}$).
- **Khả năng chịu lỗi thực tế**:
  + Xử lý an toàn file rỗng, file văn bản, ảnh trắng, ảnh cắt góc, không có camera.
- **Gợi ý hình minh họa**: Bảng tổng hợp số liệu thực nghiệm và đồ thị thời gian xử lý.

---

### SLIDE 11: DEMO SẢN PHẨM & CÁC TÍNH NĂNG NỔI BẬT
- **Video / Trình diễn trực tiếp**:
  1. Khởi động GUI: `python -m omr.gui`
  2. Nạp đáp án mẫu `Mẫu GV.png` $\to$ Đọc mã đề 567.
  3. Nạp bài làm học sinh $\to$ Bấm Chấm bài (mất < 0.3s).
  4. Xem chi tiết `Hs1.png` (10.0 điểm, 50/50 đúng) và `Hs2.png` (1.20 điểm).
  5. Sửa tay 1 câu nghi ngờ $\to$ Điểm cập nhật tức thì.
  6. Xuất báo cáo Excel 3 sheet có tô màu và CSDL SQLite.
- **Gợi ý hình minh họa**: Ảnh chụp file Excel kết quả (`TongHop`, `ChiTiet`, `DapAn`) với màu sắc trực quan.

---

### SLIDE 12: KẾT LUẬN & HƯỚNG PHÁT TRIỂN
- **Kết luận**:
  + Đề tài đã giải quyết trọn vẹn bài toán chấm trắc nghiệm OMR từ ảnh chụp thông thường.
  + Đáp ứng đầy đủ quy trình nghiệp vụ giáo viên, độ bền cao, mã nguồn mở, tài liệu hoàn chỉnh.
- **Hướng phát triển**:
  + Tích hợp mô hình AI nhẹ hỗ trợ phát hiện phiếu khi mất cả 4 góc định vị.
  + Đóng gói ứng dụng di động hỗ trợ giáo viên chấm bài ngay tại lớp học.
- **Lời cảm ơn**: Cảm ơn Thầy/Cô và các bạn đã lắng nghe!
- **Gợi ý hình minh họa**: Lời cảm ơn và thông tin liên hệ nhóm.
