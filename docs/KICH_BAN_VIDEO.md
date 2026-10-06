# KỊCH BẢN VIDEO THUYẾT TRÌNH VÀ DEMO DỰ ÁN
## ĐỀ TÀI 19: HỆ THỐNG CHẤM PHIẾU TRẢ LỜI TRẮC NGHIỆM TỰ ĐỘNG (THPT 50 CÂU)

- **Tổng thời lượng dự kiến**: 7 phút 30 giây (trong khung chuẩn 5 – 10 phút)
- **Hình thức thực hiện**: 4 thành viên lần lượt thuyết minh kết hợp quay màn hình code, sơ đồ thuật toán và demo giao diện ứng dụng.
- **Phần mềm quay video gợi ý**: OBS Studio hoặc Camtasia (độ phân giải 1080p, âm thanh rõ ràng).

---

### PHÂN CHIA THỜI LƯỢNG VÀ VAI TRÒ CỦA 4 THÀNH VIÊN

| Phần | Người trình bày | Nội dung chính | Thời lượng | Mốc thời gian |
| :---: | :--- | :--- | :---: | :---: |
| **1** | **Nguyễn Văn A**<br>(Nhóm trưởng) | Giới thiệu đề tài, Bài toán nghiệp vụ & Thuật toán Nắn phối cảnh (`detect_sheet.py`, `warp.py`) | 1 phút 50 giây | 0:00 – 1:50 |
| **2** | **Trần Thị B** | Thuật toán Đọc ô tô tròn, Mặt nạ nội tiếp & Đọc SBD, Mã đề (`bubbles.py`, `identity.py`, `grade_logic.py`) | 1 phút 40 giây | 1:50 – 3:30 |
| **3** | **Lê Văn C** | Dựng đáp án mẫu từ ảnh, Logic so khớp mã đề & Xuất báo cáo (`answer_key.py`, `scoring.py`, `export.py`) | 1 phút 40 giây | 3:30 – 5:10 |
| **4** | **Phạm Thị D** | Demo trực tiếp giao diện Tkinter, Kiểm thử độ bền & Tổng kết đề tài (`gui.py`, `webcam.py`) | 2 phút 20 giây | 5:10 – 7:30 |

---

### KỊCH BẢN CHI TIẾT TỪNG PHÚT

#### PHẦN 1: GIỚI THIỆU & THUẬT TOÁN TIỀN XỬ LÝ, NẮN PHỐI CẢNH (0:00 – 1:50)
- **Người nói**: Nguyễn Văn A
- **Hình ảnh hiển thị trên video**:
  + (0:00 – 0:30): Slide tiêu đề, logo nhóm, giới thiệu đề tài và bối cảnh nghiệp vụ.
  + (0:30 – 1:10): Sơ đồ pipeline và minh họa ảnh gốc chụp nghiêng trên bàn học.
  + (1:10 – 1:50): Mở file mã nguồn `src/omr/detect_sheet.py` và `src/omr/warp.py`, trỏ vào hàm tìm 4 marker góc và nắn phối cảnh `cv2.warpPerspective`.
- **Lời thoại (Voice-over)**:
  > *"Xin kính chào Thầy Cô và các bạn! Em là Nguyễn Văn A, đại diện Nhóm 19 trình bày đề tài: 'Hệ thống chấm phiếu trả lời trắc nghiệm tự động từ ảnh chụp mẫu THPT 50 câu'.*
  >
  > *Điểm mấu chốt trong nghiệp vụ của đề tài là: Giáo viên không cần nhập tay đáp án vào máy tính. Thay vào đó, giáo viên chỉ cần tô một tờ phiếu đáp án mẫu cho mỗi mã đề. Chương trình sẽ dùng chính pipeline xử lý ảnh để đọc ảnh đáp án mẫu, sau đó dùng làm căn cứ chấm các bài làm của học sinh.*
  >
  > *Thách thức lớn nhất khi chụp bằng điện thoại là góc chụp bị xiên, ánh sáng không đều và bóng đổ. Để giải quyết, tại module `detect_sheet.py`, nhóm em áp dụng chiến lược phát hiện 2 lớp: Ưu tiên tìm 4 ô vuông đen định vị tại 4 góc phiếu bằng phân ngưỡng thích nghi cục bộ và trích xuất contour. Sau đó, tại `warp.py`, ma trận biến đổi phối cảnh 3x3 được tính toán để nắn phẳng ảnh về kích thước chuẩn 1055 x 1491 pixel. Đồng thời, thuật toán kiểm tra cột marker phụ ở nửa trên phiếu để tự động xoay 180 độ nếu người dùng vô tình chụp ngược tờ giấy. Tiếp theo, bạn Trần Thị B sẽ trình bày về thuật toán đọc các ô tròn."*

---

#### PHẦN 2: THUẬT TOÁN ĐỌC Ô TÔ & NHẬN DIỆN THÔNG TIN (1:50 – 3:30)
- **Người nói**: Trần Thị B
- **Hình ảnh hiển thị trên video**:
  + (1:50 – 2:30): Mở file `config/config.json` và `src/omr/bubbles.py`. Chiếu hình phóng to ô tròn có mặt nạ tròn nội tiếp (đường tròn bán kính 8 px).
  + (2:30 – 3:00): Mở file `src/omr/grade_logic.py`, chỉ rõ các ngưỡng `0.38` (HOP_LE), `0.24` (BLANK), và trường hợp MULTI, AMBIGUOUS.
  + (3:00 – 3:30): Mở file `src/omr/identity.py`, chiếu đoạn mã đọc từng cột Số báo danh và Mã đề thi.
- **Lời thoại (Voice-over)**:
  > *"Chào Thầy Cô, em là Trần Thị B. Sau khi tờ phiếu đã được nắn thẳng hoàn hảo, bước tiếp theo là đọc chính xác các ô đã tô.*
  >
  > *Tại module `bubbles.py`, nhóm không áp dụng một ngưỡng toàn cục mà dùng `cv2.adaptiveThreshold` theo từng vùng lân cận 41 pixel. Nhờ đó, ngay cả khi phiếu bị bóng đổ che khuất một góc, các nét chì vẫn nổi bật thành màu trắng trên nền đen.*
  >
  > *Một sáng tạo kỹ thuật quan trọng của nhóm là: Viền đen in sẵn của mẫu phiếu có bán kính khoảng 11 pixel. Để loại bỏ hoàn toàn viền in gây nhiễu, nhóm tạo một mặt nạ tròn nội tiếp với bán kính chỉ 8 pixel, nằm trọn trong lòng ô. Tỉ lệ lấp đầy fill_ratio được tính bằng tổng số pixel trắng chia cho diện tích mặt nạ 197 pixel.*
  >
  > *Tại `grade_logic.py`, nếu có từ 2 ô vượt ngưỡng 0.38 thì kết luận là MULTI - tô nhiều ô; nếu không ô nào đạt 0.24 thì là BLANK - bỏ trống; nếu một ô vượt trội rõ ràng thì là HỢP LỆ; còn vùng phân vân sẽ được đánh dấu AMBIGUOUS để giáo viên kiểm tra.*
  >
  > *Tương tự, tại `identity.py`, khối SBD 4 cột và Mã đề 3 cột được quét theo từng cột để lấy hàng có fill_ratio lớn nhất. Tiếp theo, bạn Lê Văn C sẽ trình bày quy trình so khớp và chấm điểm."*

---

#### PHẦN 3: DỰNG ĐÁP ÁN MẪU, CHẤM ĐIỂM & XUẤT DỮ LIỆU (3:30 – 5:10)
- **Người nói**: Lê Văn C
- **Hình ảnh hiển thị trên video**:
  + (3:30 – 4:10): Mở file `src/omr/answer_key.py`, giải thích cách duyệt thư mục `data/answer_key_images/` và hàm `dung_tu_dien_dap_an()`.
  + (4:10 – 4:40): Mở file `src/omr/scoring.py`, chỉ vào hàm `cham_mot_bai()` và thuật toán phát hiện nghi trùng bài.
  + (4:40 – 5:10): Mở file `src/omr/export.py`, chiếu lướt đoạn mã tạo 3 sheet Excel (`TongHop`, `ChiTiet`, `DapAn`) và 4 bảng SQLite.
- **Lời thoại (Voice-over)**:
  > *"Kính chào Thầy Cô, em là Lê Văn C. Em xin phép trình bày về giai đoạn nghiệp vụ cốt lõi: Dựng đáp án mẫu và Chấm bài.*
  >
  > *Tại `answer_key.py`, chương trình gọi hàm `read_sheet()` dùng chung cho từng ảnh đáp án mẫu. Toàn bộ 50 câu của phiếu mẫu bắt buộc phải hợp lệ 100%, không được có câu bỏ trống hay nghi ngờ, vì nếu đáp án mẫu sai sẽ ảnh hưởng đến cả lớp. Kết quả được lưu vào từ điển ánh xạ theo từng Mã đề.*
  >
  > *Khi chấm bài học sinh ở `scoring.py`, hệ thống lấy Mã đề đọc được từ bài làm để tìm đúng đáp án chuẩn tương ứng. Mỗi câu trả lời của học sinh được so sánh với đáp án chuẩn: nếu đúng được cộng 0.2 điểm; nếu sai, bỏ trống hoặc tô nhiều ô thì nhận 0 điểm. Đặc biệt, hệ thống có cơ chế tự động phát hiện nghi trùng bài nếu hai bài thi có cùng SBD và Mã đề để tránh nhầm lẫn.*
  >
  > *Toàn bộ kết quả được xuất ra file Excel bằng OpenPyXL tại `export.py` với 3 sheet rõ ràng: sheet Tổng hợp danh sách, sheet Chi tiết 50 câu có tô màu xanh lá cho câu đúng và đỏ cho câu sai, cùng sheet Đối chiếu đáp án chuẩn. Dữ liệu cũng đồng thời được lưu vào cơ sở dữ liệu SQLite hỗ trợ upsert khi chạy lại. Sau đây, bạn Phạm Thị D sẽ demo trực tiếp giao diện người dùng."*

---

#### PHẦN 4: DEMO TRỰC TIẾP GIAO DIỆN & TỔNG KẾT ĐỀ TÀI (5:10 – 7:30)
- **Người nói**: Phạm Thị D
- **Hình ảnh hiển thị trên video**:
  + (5:10 – 5:30): Mở terminal gõ `python -m omr.gui`, giao diện Tkinter hiện lên với tông màu chuyên nghiệp.
  + (5:30 – 6:00): BƯỚC 1: Bấm "Chọn ảnh đáp án mẫu", chọn `Mẫu GV.png` $\to$ Bảng hiện Mã đề `567` và 50 đáp án chuẩn.
  + (6:00 – 6:30): BƯỚC 2 & 3: Bấm "Chọn thư mục ảnh bài làm", chọn thư mục `data/student_images/` $\to$ Bấm "Bắt đầu chấm". Thanh tiến trình chạy mượt mà nhờ đa luồng `threading`.
  + (6:30 – 7:00): Bấm vào dòng học sinh `Hs1.png` $\to$ Khung ảnh bên phải hiện ảnh phiếu nắn khoanh tròn 50/50 màu xanh lá, đạt 10.00 điểm. Bấm vào `Hs2.png` $\to$ Điểm 1.20, hiện các câu sai màu đỏ. Thử click sửa tay 1 câu nghi ngờ $\to$ Điểm số tự động cập nhật ngay trên giao diện.
  + (7:00 – 7:15): Bấm nút "Xuất Excel" và mở file `outputs/ketqua.xlsx` vừa xuất để người xem thấy 3 sheet hoàn chỉnh.
  + (7:15 – 7:30): Slide tổng kết kết quả kiểm thử (64 bài biến dạng nặng, độ chính xác 99.38%, tốc độ 0.15s/bài). Lời chào kết thúc.
- **Lời thoại (Voice-over)**:
  > *"Em là Phạm Thị D. Sau đây em xin demo trực tiếp giao diện người dùng Tkinter do nhóm xây dựng.*
  >
  > *Giao diện được thiết kế bám sát 3 bước nghiệp vụ của giáo viên: Bước 1 nạp đáp án mẫu, Bước 2 chọn bài làm học sinh, và Bước 3 chấm thi.*
  >
  > *Đầu tiên, em bấm 'Chọn ảnh đáp án mẫu' và nạp file 'Mẫu GV.png'. Hệ thống ngay lập tức nhận diện Mã đề 567 cùng 50 đáp án chuẩn. Giáo viên có thể bấm nút xác nhận hoặc sửa tay nếu muốn.*
  >
  > *Tiếp theo ở Bước 2, em chọn thư mục bài làm của học sinh. Ứng dụng cũng hỗ trợ chụp trực tiếp từ webcam nếu máy tính có kết nối camera.*
  >
  > *Ở Bước 3, em bấm 'Bắt đầu chấm'. Nhờ áp dụng kỹ thuật đa luồng threading, giao diện hoàn toàn không bị giật lag khi chấm cả danh sách. Kết quả hiện ra ngay lập tức: Học sinh 1 đạt 10.0 điểm tuyệt đối; Học sinh 2 đạt 1.20 điểm.*
  >
  > *Khi em bấm vào bài của Học sinh 1, khung bên trái hiển thị ảnh chụp gốc, khung bên phải hiển thị ảnh phiếu đã nắn thẳng với các vòng tròn màu xanh lá đánh dấu câu đúng. Với Học sinh 2, các câu sai được đánh dấu màu đỏ kèm viền xanh đáp án chuẩn. Nếu phát hiện câu bị nghi ngờ hoặc học sinh quên tô mã đề, giáo viên có thể sửa trực tiếp và điểm số được tính lại ngay lập tức.*
  >
  > *Cuối cùng, em bấm 'Xuất Excel'. File Excel mở ra với đầy đủ bảng tổng hợp, chi tiết màu sắc và đáp án đối chiếu.*
  >
  > *Qua thử nghiệm trên 64 phiếu thi biến dạng nặng, hệ thống đạt độ chính xác 99.38% ở mức câu, 100% ở SBD và Mã đề, tốc độ xử lý chỉ 0.15 giây một phiếu. Nhóm 19 xin chân thành cảm ơn Thầy Cô đã theo dõi phần trình bày của nhóm!"*
