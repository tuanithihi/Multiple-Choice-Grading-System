# 20 CÂU HỎI ÔN TẬP VÀ TRẢ LỜI VẤN ĐÁP BẢO VỆ ĐỀ TÀI
## ĐỀ TÀI 19: HỆ THỐNG CHẤM PHIẾU TRẮC NGHIỆM TỰ ĐỘNG (THPT 50 CÂU)

> **Mục đích**: Tài liệu này giúp tất cả các thành viên trong nhóm nắm chắc mã nguồn thực tế và tự tin trả lời đúng trọng tâm các câu hỏi chuyên sâu từ Giảng viên phản biện khi bảo vệ đề tài.

---

### PHẦN I: KIẾN TRÚC HỆ THỐNG & NGHIỆP VỤ (CÂU 1 – 5)

#### Câu 1: Vì sao chương trình đọc đáp án chuẩn từ ảnh phiếu đáp án mẫu bằng cùng một pipeline với bài làm học sinh mà không yêu cầu nhập file text/Excel?
- **Trả lời**: 
  - Mô phỏng chính xác quy trình tự nhiên của giáo viên: Giáo viên chỉ cần tô một phiếu đáp án mẫu cho mỗi mã đề như học sinh.
  - Tái sử dụng tối đa mã nguồn (`src/omr/read_sheet.py`), đảm bảo tính nhất quán giữa khâu nạp đáp án và khâu chấm bài.
  - Giáo viên không mất công gõ tay 50 đáp án cho từng mã đề, tránh lỗi gõ nhầm.

#### Câu 2: Chuyện gì xảy ra nếu ảnh phiếu đáp án mẫu của giáo viên bị mờ, rách hoặc có câu chưa tô/tô nhiều ô?
- **Trả lời**: 
  - Module `src/omr/answer_key.py` có hàm kiểm định chất lượng nghiêm ngặt `LoiDapAnMau`.
  - Phiếu đáp án mẫu bắt buộc phải có đủ 50 câu hợp lệ (chỉ nhận A, B, C, D; không chấp nhận `BLANK`, `MULTI` hay `AMBIGUOUS`).
  - Nếu ảnh mẫu bị lỗi, hệ thống từ chối nạp và cảnh báo ngay lập tức, vì nếu đáp án mẫu sai sẽ dẫn đến chấm sai cho toàn bộ học sinh trong lớp. Trên giao diện Tkinter, giáo viên cũng có thể kiểm tra và sửa tay trước khi chấm.

#### Câu 3: Khi Mã đề trên bài làm của học sinh không khớp với bất kỳ phiếu đáp án mẫu nào thì hệ thống xử lý thế nào?
- **Trả lời**: 
  - Trong `src/omr/scoring.py`, bài làm được gán trạng thái `CHUA_CHAM` với lý do rõ ràng: *"Mã đề 'xyz' không có trong từ điển đáp án chuẩn"*, điểm số tạm thời là `0.0`.
  - Chương trình **không bị sập (crash)**, vẫn tiếp tục chấm các bài tiếp theo trong danh sách.
  - Trên giao diện, giáo viên có thể dùng tính năng sửa tay Mã đề (`sua_tay_ma_de()`) để chấm lại ngay lập tức.

#### Câu 4: Làm thế nào chương trình phát hiện và cảnh báo hai bài làm bị trùng Số báo danh và Mã đề?
- **Trả lời**: 
  - Trong `src/omr/scoring.py`, sau khi chấm cả danh sách, hệ thống duyệt một bảng băm `(sbd, ma_de)`. Nếu phát hiện có từ 2 bài trở lên trùng cả SBD và Mã đề hợp lệ, cờ `nghi_trung_bai: true` được kích hoạt.
  - Hệ thống ghi rõ danh sách các file trùng vào mục cảnh báo (`warnings`), hiển thị trên console và thêm cảnh báo vào cột *Ghi chú* trong file Excel.

#### Câu 5: Vì sao hệ thống chọn kích thước chuẩn khi nắn phẳng là 1055 × 1491 pixel?
- **Trả lời**: 
  - Kích thước này đúng bằng kích thước pixel thực tế của mẫu phiếu THPT chuẩn trong tập dữ liệu gốc (`data/answer_key_images/Mẫu GV.png`).
  - Tỉ lệ $1491 / 1055 \approx 1.4132$, gần như trùng khớp tuyệt đối với tỉ lệ vàng của khổ giấy quốc tế ISO A4 ($\sqrt{2} \approx 1.4142$).

---

### PHẦN II: THỊ GIÁC MÁY TÍNH & XỬ LÝ ẢNH (CÂU 6 – 12)

#### Câu 6: Hệ thống phát hiện 4 góc của tờ giấy thi bằng thuật toán gì? Nếu nền bàn tối bao quanh tờ giấy thì có bị lỗi không?
- **Trả lời**: 
  - Hệ thống dùng chiến lược 2 lớp trong `src/omr/detect_sheet.py`: Ưu tiên tìm 4 ô vuông đen (Marker) ở 4 góc; dự phòng tìm tứ giác giấy bằng Canny + `approxPolyDP`.
  - Khi nền bàn tối bao quanh giấy, contour ngoài cùng sẽ là toàn bộ ảnh. Nhóm đã giải quyết bằng cách dùng `cv2.findContours` với chế độ `cv2.RETR_LIST` thay vì `RETR_EXTERNAL`. Chế độ này trích xuất toàn bộ contour lồng bên trong, tìm thấy 100% các ô marker góc mà không bị nền bàn ảnh hưởng.

#### Câu 7: Làm sao hệ thống biết một ảnh chụp bị ngược 180 độ và tự xoay lại đúng chiều?
- **Trả lời**: 
  - Trong `src/omr/warp.py` (hàm `kiem_tra_nguoc_180`), hệ thống dựa vào đặc trưng bất đối xứng của mẫu phiếu THPT: Cột marker phân cách và vạch định vị timing marks xuất hiện ở tọa độ $x \sim 720\text{ px}$ tại nửa trên phiếu, nhưng không xuất hiện ở nửa dưới.
  - Thuật toán phân ngưỡng thích nghi cục bộ trên ảnh nắn và đếm mật độ điểm đen ở nửa trên so với nửa dưới. Nếu mật độ ở nửa dưới vượt trội, ảnh bị ngược $\to$ gọi `cv2.rotate(warped, cv2.ROTATE_180)` để xoay lại.

#### Câu 8: Vì sao hệ thống không dùng một ngưỡng nhị phân cố định (như 127) mà dùng Adaptive Threshold?
- **Trả lời**: 
  - Trong điều kiện chụp thực tế (điện thoại, webcam), ánh sáng thường không đồng đều, có bóng đổ nghiêng của người chụp hoặc bóng đèn.
  - Ngưỡng cố định 127 sẽ làm vùng bị bóng đổ biến hoàn toàn thành màu đen (bị nhận nhầm là tô hết).
  - Phân ngưỡng thích nghi (`cv2.adaptiveThreshold` với Gaussian weights, $ksize = 41\text{ px}$) tính ngưỡng độc lập cho từng ô tròn theo vùng lân cận, loại bỏ hoàn toàn ảnh hưởng của bóng đổ.

#### Câu 9: Mặt nạ hình tròn nội tiếp (Circular Mask) giải quyết bài toán gì và có kích thước bao nhiêu?
- **Trả lời**: 
  - Trên mẫu phiếu in sẵn, mỗi lựa chọn đã có một vòng tròn mực in màu đen bao quanh ($R_{\text{in}} \approx 11\text{ px}$). Nếu tính toán toàn bộ ô vuông bao quanh, viền mực này sẽ bị tính vào nét chì tô.
  - Giải pháp: Tạo mặt nạ hình tròn nhị phân có bán kính $R = 8\text{ px}$ (`ban_kinh_o_pixel` trong `config.json`), diện tích 197 pixel. Bán kính này nằm trọn trong lòng ô tròn, triệt tiêu 100% viền in sẵn.

#### Câu 10: Tỉ lệ lấp đầy (Fill Ratio) được tính theo công thức nào?
- **Trả lời**: 
  $$\text{fill\_ratio} = \frac{\text{Số pixel trắng sau nhị phân đảo trong mặt nạ}}{\text{Tổng số pixel của mặt nạ (197 px)}}$$
  - Sau nhị phân đảo, nét chì là pixel trắng (giá trị 255), nền giấy là pixel đen (0). Giá trị fill_ratio nằm trong khoảng từ $0.0$ (hoàn toàn trắng) đến $1.0$ (tô kín đen).

#### Câu 11: Quy tắc phân loại đáp án của một câu hỏi hoạt động như thế nào?
- **Trả lời** (trong `src/omr/grade_logic.py`):
  - **MULTI** (Tô nhiều ô): Có từ 2 ô trở lên có fill_ratio $\ge 0.38$ (ngưỡng tô).
  - **BLANK** (Bỏ trống): Cả 4 ô đều có fill_ratio $< 0.24$ (ngưỡng trống).
  - **HỢP LỆ** (A/B/C/D): Đúng 1 ô $\ge 0.38$ và khoảng chênh lệch với ô cao thứ nhì $\ge 0.10$.
  - **AMBIGUOUS** (Nghi ngờ): Ô cao nhất nằm trong đoạn $[0.24, 0.38)$ (tô quá mờ) hoặc chênh lệch với ô thứ nhì $< 0.10$ (tẩy xóa không sạch).

#### Câu 12: Tại sao mã nguồn tuyệt đối không hardcode tọa độ các ô tròn trong code Python?
- **Trả lời**: 
  - Toàn bộ tọa độ gốc của các khối, bước nhảy giữa các câu và bán kính ô đều được lưu trong file cấu hình JSON (`config/config.json`).
  - Thiết kế này giúp hệ thống dễ dàng mở rộng, thay đổi mẫu phiếu khác (phiếu 40 câu, phiếu 100 câu) mà chỉ cần cập nhật file JSON, không phải sửa và biên dịch lại mã nguồn logic.

---

### PHẦN III: LẬP TRÌNH & ĐẶC TẢ PHẦN MỀM (CÂU 13 – 17)

#### Câu 13: Làm thế nào chương trình xử lý được đường dẫn file chứa tiếng Việt có dấu trên hệ điều hành Windows?
- **Trả lời**: 
  - Hàm chuẩn `cv2.imread()` và `cv2.imwrite()` trên Windows sử dụng ANSI string, gây lỗi `None` khi gặp đường dẫn Unicode tiếng Việt (ví dụ: `Thị giác máy tính`).
  - Trong `src/omr/samples.py`, nhóm thay thế bằng:
    + Đọc ảnh: `np.fromfile(duong_dan, dtype=np.uint8)` kết hợp `cv2.imdecode(..., cv2.IMREAD_COLOR)`.
    + Ghi ảnh: `cv2.imencode('.png', img)[1].tofile(duong_dan)`.

#### Câu 14: Tại sao khi bấm "Bắt đầu chấm bài" trên giao diện Tkinter, cửa sổ không bị đơ (Not Responding)?
- **Trả lời**: 
  - Nhóm tách biệt luồng xử lý: Quá trình đọc ảnh và tính điểm chạy trên một luồng nền độc lập (`threading.Thread(target=..., daemon=True)`).
  - Luồng giao diện Tkinter vẫn chạy `mainloop()` bình thường. Luồng nền cập nhật thanh tiến trình `ttk.Progressbar` an toàn qua phương thức `root.after(0, ...)`.

#### Câu 15: Mô hình phân tách Controller và View trong `src/omr/gui.py` đem lại lợi ích gì?
- **Trả lời**: 
  - Lớp `OMRController` đóng gói toàn bộ trạng thái nghiệp vụ (nạp đáp án mẫu, quản lý bài làm, tính lại điểm khi sửa tay, gọi xuất Excel/SQLite).
  - Lợi ích: Có thể viết unit test và integration test tự động cho toàn bộ luồng nghiệp vụ trên môi trường headless (máy chủ không có màn hình) mà không cần khởi tạo widget Tkinter.

#### Câu 16: Cơ sở dữ liệu SQLite trong dự án gồm những bảng nào và cơ chế Upsert hoạt động ra sao?
- **Trả lời**: 
  - Gồm 4 bảng: `dap_an_chuan`, `thi_sinh`, `bai_lam`, `chi_tiet_cau`.
  - Bảng `bai_lam` có ràng buộc duy nhất `UNIQUE(sbd, ma_de)`. Khi người dùng chấm lại cùng một bài thi hoặc sửa tay đáp án, câu lệnh `INSERT INTO ... ON CONFLICT(sbd, ma_de) DO UPDATE` sẽ tự động cập nhật bản ghi cũ thay vì tạo bản ghi trùng lặp.

#### Câu 17: Cấu trúc file Excel kết quả (`ketqua.xlsx`) gồm những sheet nào và có điểm gì nổi bật?
- **Trả lời**: 
  - Gồm 3 sheet chuẩn:
    1. `TongHop`: Danh sách thí sinh, SBD, Mã đề, số đúng/sai/trống, điểm số và ghi chú nghi trùng bài.
    2. `ChiTiet`: Chi tiết 50 câu của từng thí sinh, tô màu trực quan bằng OpenPyXL (xanh lá cho câu đúng, đỏ cho câu sai, vàng cho câu nghi ngờ).
    3. `DapAn`: Bảng đối chiếu đáp án chuẩn theo từng mã đề.
  - Ngoài ra còn có sheet `Loi` lưu vết các file ảnh bị hỏng không đọc được.

---

### PHẦN IV: THỬ NGHIỆM, TỐI ƯU & HƯỚNG MỞ RỘNG (CÂU 18 – 20)

#### Câu 18: Kết quả kiểm thử trên tập ảnh biến dạng nặng đạt các chỉ số kỹ thuật như thế nào?
- **Trả lời**: 
  - Đã kiểm thử trên tập **64 phiếu học sinh biến dạng mạnh** (nghiêng phối cảnh $22^\circ$, bóng đổ $50\%$ diện tích, giảm sáng $45\%$, nhiễu muối tiêu, nén JPEG $Q=50$):
    + Độ chính xác đọc từng câu: **99.38%** (3180/3200 câu).
    + Độ chính xác đọc SBD và Mã đề: **100.0%** (64/64 phiếu).
    + Tỉ lệ crash chương trình: **0.0%**.
    + Tốc độ xử lý: **0.157 giây/phiếu** (vượt xa chỉ tiêu $\le 3\text{ giây}$).

#### Câu 19: Nếu máy tính không có webcam hoặc camera bị hỏng, chức năng "Chụp từ webcam" xử lý như thế nào?
- **Trả lời**: 
  - Module `src/omr/webcam.py` có hàm `kiem_tra_camera()` mở thử thiết bị `cv2.VideoCapture(0)`.
  - Nếu không tìm thấy camera, hệ thống hiển thị thông báo lỗi nhẹ nhàng bằng tiếng Việt và vô hiệu hóa nút chụp, tuyệt đối không làm chương trình bị sập.

#### Câu 20: Nếu được phát triển tiếp, nhóm sẽ nâng cấp những tính năng gì cho hệ thống?
- **Trả lời**: 
  - Tích hợp mạng nơ-ron MobileNet nhẹ để phát hiện góc phiếu khi cả 4 marker đen bị rách mất.
  - Tích hợp module OCR nhận diện chữ viết tay để đọc họ tên thí sinh ở phần ghi chú.
  - Xây dựng ứng dụng di động hoàn chỉnh để giáo viên có thể quét và chấm trực tiếp bằng camera điện thoại tại lớp học.
