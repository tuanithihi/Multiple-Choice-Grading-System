# Nhật ký tiến độ – Chấm phiếu trắc nghiệm OMR

| Giai đoạn | Mô tả | Trạng thái | Ngày hoàn thành | Số test | Pass | Ghi chú |
|-----------|--------|-----------|-----------------|---------|------|---------|
| 1 | Cấu trúc dự án & khung chương trình | ✅ Đã qua cổng | 2026-09-28 22:06 | 52 | 52 | Cấu trúc đủ, CLI chạy được |
| 2 | Thêm ảnh thật & tiền xử lý ảnh | ✅ Đã qua cổng | 2026-09-28 23:02 | 13 | 13 | Bố cục xác nhận, ảnh preview chuẩn |
| 3 | Phát hiện biên & nắn phối cảnh | ✅ Đã qua cổng | 2026-09-28 23:26 | 7 | 7 | Nắn phẳng 1055x1491, tự xoay 180° |
| 4 | Đọc ô tô (bubbles) | ✅ Đã qua cổng | 2026-09-29 12:30 | 12 | 12 | Đọc 50 câu, 100% sạch, 100% BLANK/MULTI |
| 5 | Đọc SBD, mã đề & đọc phiếu hoàn chỉnh | ✅ Đã qua cổng | 2026-09-29 12:40 | 10 | 10 | Đọc SBD, Mã đề 100%, hoàn thiện read_sheet() |
| 6 | Dựng đáp án mẫu & chấm điểm | ✅ Đã qua cổng | 2026-09-29 12:45 | 11 | 11 | Đáp án đọc từ ảnh, chấm điểm 100%, xuất Excel & DB |
| 7 | Tăng độ bền ảnh thực tế & Chấm hàng loạt | ✅ Đã qua cổng | 2026-09-29 13:25 | 7 | 7 | 64 phiếu biến dạng nặng (99.38% câu, 100% ID, 0.157s/phiếu) |
| 8 | Giao diện Tkinter | ✅ Đã qua cổng | 2026-09-29 13:30 | 7 | 7 | 3 bước trực quan, đa luồng, sửa tay, ảnh nắn kèm đáp án |
| 9 | Kiểm thử tổng thể, dọn dẹp & đóng gói | ✅ Đã qua cổng | 2026-09-29 13:45 | 5 | 5 | Clean venv, E2E CLI & GUI, 100% tài liệu docs/ |

---

## Chi tiết từng giai đoạn

### Giai đoạn 1 – Cấu trúc dự án & khung chương trình
- **Ngày**: 2026-09-28 22:06
- **Số test**: 52 | **Pass**: 52 | **Fail**: 0
- **Thời gian chạy test**: 1.58s

**Quyết định thiết kế quan trọng**:
1. **Unicode path fix**: OpenCV trên Windows không đọc được đường dẫn chứa ký tự
   tiếng Việt. Dùng `numpy.fromfile()` + `cv2.imdecode()` thay vì `cv2.imread()`.
   Tương tự, dùng `cv2.imencode()` + `ndarray.tofile()` thay vì `cv2.imwrite()`.
2. **UTF-8 stdout/stderr**: Windows console mặc định dùng cp1252, không hiển thị
   được tiếng Việt. Thêm `io.TextIOWrapper` ở đầu `main.py` để ép UTF-8.
3. **Config schema validation**: Dùng dot-path notation (vd: `"anh.chieu_rong"`)
   để kiểm tra khóa lồng nhau, hỗ trợ nhiều kiểu (int|float).
4. **Config nháp**: Tất cả giá trị bố cục đánh dấu `chua_xac_nhan: true`,
   sẽ được hiệu chỉnh khi có ảnh phiếu thật ở Giai đoạn 2.

### Giai đoạn 2 – Thêm ảnh thật & tiền xử lý ảnh
- **Ngày**: 2026-09-28 23:02
- **Số test**: 13 | **Pass**: 13 | **Fail**: 0
- **Thời gian chạy test**: 1.45s

**Phân tích ảnh thực tế**:
1. **Tập ảnh**:
   - `data/answer_key_images/Mẫu GV.png`: 1055 × 1491 px, 1.34 MB (đáp án mẫu).
   - `data/student_images/Hs1.png`: 1055 × 1491 px, 1.29 MB (bài làm học sinh 1).
   - `data/student_images/Hs2.png`: 1055 × 1491 px, 1.32 MB (bài làm học sinh 2).
2. **Bố cục phiếu**:
   - **4 Marker góc**: 4 ô vuông đen định vị nằm tại 4 góc chuẩn của phiếu.
   - **50 câu hỏi**: Chia thành 2 cột lớn (Câu 1-25 và Câu 26-50), mỗi cột gồm 5 khối (5 câu/khối, 4 đáp án A/B/C/D).
   - **Số báo danh (SBD)**: Trên phiếu học sinh làm bài (`Hs1.png`, `Hs2.png`), khối SBD có 4 cột (chữ số từ 0 đến 9). Mẫu GV hiển thị 6 cột (để trống).
   - **Mã đề thi**: Gồm 3 cột (chữ số từ 0 đến 9).
3. **Nhận xét bằng mắt về ảnh đáp án mẫu (`Mẫu GV.png`)**:
   - **50 câu hỏi**: Đã được tô đầy đủ 50 câu (mỗi câu 1 đáp án).
   - **Mã đề**: Trên ảnh `Mẫu GV.png`, khối Mã đề thi hiện đang để trống (chưa tô ô nào).
   - **SBD**: Trên ảnh `Mẫu GV.png`, khối SBD cũng để trống.
   - Trên ảnh học sinh (`Hs1.png`, `Hs2.png`): Mã đề đã tô là "567", SBD đã tô là "1234".
4. **Quyết định cấu hình & module**:
   - Viết `src/omr/samples.py` quản lý nạp ảnh Unicode, bắt lỗi file hỏng không gây crash.
   - Viết `src/omr/preprocess.py` với các giải thuật cổ điển (grayscale, blur, Canny, Otsu).
   - Cập nhật `config/config.json` với tọa độ thực tế 1055 × 1491 px, chuyển `chua_xac_nhan: false`.
   - Sinh ảnh trực quan hóa bố cục `outputs/debug/layout_preview_*.png`.

### Giai đoạn 3 – Tiền xử lý, phát hiện phiếu & nắn phối cảnh
- **Ngày**: 2026-09-28 23:26
- **Số test**: 7 (bao gồm 20 biến thể kiểm thử giả lập) | **Pass**: 7 | **Fail**: 0
- **Thời gian chạy test**: 4.69s

**Quyết định thiết kế & kết quả thực nghiệm**:
1. **Chiến lược phát hiện 2 lớp trong `detect_sheet.py`**:
   - *Ưu tiên (a)*: Tìm 4 ô đánh dấu góc (marker vuông đen) dựa trên đặc trưng hình học (tỉ lệ cạnh 0.65-1.55, độ đặc `extent >= 0.70`, tứ giác lồi diện tích > 20% ảnh). Cả 3 ảnh thật đều được phát hiện chính xác bằng marker.
   - *Dự phòng (b)*: Canny + Morphology Close + `approxPolyDP` tìm tứ giác viền giấy trắng trên nền bàn. Bổ sung kiểm tra tỉ lệ khung hình A4 (1.10 - 1.90) và độ sáng nền trong tứ giác (> 130) để triệt tiêu việc nhận nhầm viền ảnh hoặc nhiễu ngẫu nhiên.
   - Báo lỗi rõ ràng bằng tiếng Việt (`LoiKhongTimThayPhieu`) khi không tìm thấy phiếu, tuyệt đối không trả về kết quả rác.
2. **Nắn phối cảnh & Tự động sửa chiều xoay trong `warp.py`**:
   - Dùng `cv2.getPerspectiveTransform` + `cv2.warpPerspective` đưa ảnh về kích thước chuẩn `1055 × 1491 px`.
   - Tự động phát hiện ảnh chụp ngang (`w > h`) và xoay 90° sang đứng.
   - Tự động phát hiện ảnh bị ngược 180° dựa vào 2 marker đen đặc trưng tại cột `x ~ 720 px` ở nửa trên phiếu (và không xuất hiện ở nửa dưới), tự xoay lại đúng chiều xuôi.
3. **Độ chính xác trên biến thể giả lập**:
   - Kiểm thử trên 20 biến thể (xoay ±15°, xoay 180°, nghiêng phối cảnh, nền bàn lộn xộn, đổi độ sáng ±30%, nhiễu Gaussian).
   - Tỉ lệ phát hiện đúng: **100% (20/20 đạt, yêu cầu >= 95%)**.
   - Sai số góc tìm được so với góc thật: **~0.10% cạnh ảnh (yêu cầu < 1.5%)**, vượt chuẩn gấp 15 lần.
4. **Nghiệm thu ảnh thật**:
   - Toàn bộ ảnh thật (`Mẫu GV.png`, `Hs1.png`, `Hs2.png`) được nắn phẳng hoàn hảo, khớp 100% các ô ROI của câu hỏi, SBD, mã đề và marker.

### Giai đoạn 4 – Đọc 50 câu trả lời trắc nghiệm
- **Ngày**: 2026-09-29 12:30
- **Số test**: 12 (bao gồm 60 phiếu kiểm thử giả lập = 3000 lượt đọc câu) | **Pass**: 12 | **Fail**: 0
- **Thời gian chạy test**: 5.91s

**Quyết định thiết kế & kết quả thực nghiệm**:
1. **Giải thuật tính tỉ lệ tô ô tròn (`bubbles.py`)**:
   - Dùng nhị phân hóa Otsu đảo (nét chì/mực thành trắng 255 trên nền đen 0).
   - Tạo mặt nạ hình tròn nhị phân nội tiếp với bán kính $R = 8\text{ px}$ (`ban_kinh_o_pixel` trong config). Diện tích mặt nạ là 197 pixel.
   - Bán kính này nằm trọn trong lòng ô tròn, hoàn toàn loại bỏ viền đen in sẵn của mẫu phiếu ($R \approx 11\text{ px}$), triệt tiêu nhiễu viền.
   - Tỉ lệ tô: $\text{fill\_ratio} = \frac{\text{số pixel trắng trong mặt nạ}}{\text{tổng pixel mặt nạ}}$.
2. **Logic quyết định đáp án (`grade_logic.py`)**:
   - $\ge 2$ ô có $\text{fill\_ratio} \ge 0.38 \to \text{MULTI}$ (tô nhiều ô).
   - Tất cả các ô $< 0.24 \to \text{BLANK}$ (bỏ trống).
   - Ô cao nhất nằm trong $[0.24, 0.38)$, hoặc $\ge 0.38$ nhưng chênh lệch với ô thứ nhì $< 0.10$ và ô nhì $\ge 0.24 \to \text{AMBIGUOUS}$ (nghi ngờ, đánh dấu kiểm tra).
   - Đúng 1 ô $\ge 0.38$ và chênh lệch với ô nhì $\ge 0.10 \to \text{HOP\_LE}$ (đáp án hợp lệ A/B/C/D).
   - Không hard-code bất kỳ tọa độ nào; toàn bộ tọa độ và bước nhảy lấy từ `config.json`.
3. **Hiển thị trực quan và Debug**:
   - Khoanh tròn xanh lá cho ô tô hợp lệ kèm nhãn (ví dụ `01:C`).
   - Khoanh tròn đỏ cho các ô vi phạm tô nhiều (MULTI) kèm nhãn `01:MUL`.
   - Khoanh tròn vàng cho ô sát ngưỡng nghi ngờ (AMBIGUOUS) kèm nhãn `01:AMB`.
   - Ghi nhận `01:--` cho câu bỏ trống (BLANK).
   - Xuất ảnh debug ra `outputs/debug/bubbles_preview_*.png`.
4. **Kết quả kiểm thử trên ảnh giả lập (30 phiếu sạch + 30 phiếu nghiêng/nhiễu)**:
   - **Phiếu sạch (30 phiếu, 1500 câu)**:
     + Độ chính xác: **100.00% (1500/1500, yêu cầu $\ge 99\%$)**.
     + Nhận diện BLANK có chủ đích: **100.0% (60/60)**.
     + Nhận diện MULTI có chủ đích: **100.0% (60/60)**.
   - **Phiếu nghiêng, xoay, nhiễu qua toàn bộ Pipeline Giai đoạn 3 (30 phiếu, 1500 câu)**:
     + Độ chính xác: **100.00% (1500/1500, yêu cầu $\ge 97\%$)**.
5. **Nghiệm thu ảnh thực tế**:
   - `Mẫu GV.png`: Đọc đúng **50/50 câu hợp lệ** (100%), 0 BLANK, 0 MULTI, 0 AMBIGUOUS. Chuỗi đáp án: `CBDACBDACBDACBDCABDCBDACBDACBDCADBCBDACBDCABDCBADC`.
   - `Hs1.png`: Đọc được **50/50 câu hợp lệ**, khớp 100% với đáp án Mẫu GV.
   - `Hs2.png`: Đọc được 27 câu hợp lệ, 12 câu bỏ trống (BLANK), 11 câu nghi ngờ mờ/tẩy (AMBIGUOUS), không có câu MULTI. Khớp hoàn toàn với quan sát trực quan trên phiếu học sinh làm bài dở dang.

### Giai đoạn 5 – Đọc Số báo danh, Mã đề & Hoàn thiện read_sheet()
- **Ngày**: 2026-09-29 12:40
- **Số test**: 10 (bao gồm 100 lượt kiểm thử trên phiếu giả lập + ảnh thật) | **Pass**: 10 | **Fail**: 0
- **Thời gian chạy test**: 9.62s

**Quyết định thiết kế & kết quả thực nghiệm**:
1. **Module `identity.py` (Đọc SBD và Mã đề)**:
   - Quét từng cột từ trái sang phải, mỗi cột tính `fill_ratio` của 10 hàng tương ứng chữ số từ `0` đến `9`.
   - Toàn bộ tọa độ gốc `pixel_x`, `pixel_y`, `cot_x_offsets`, `hang_y_offsets` và bán kính ô $R = 7\text{ px}$ được lấy từ `config.json` (không hard-code).
   - Xử lý các ca bất thường:
     + Cột không tô: trả ký tự `"?"`, trạng thái `BLANK`, ghi nhận cảnh báo `"Cột X không được tô"`.
     + Cột tô $\ge 2$ ô: trả ký tự `"?"`, trạng thái `MULTI`, ghi nhận cảnh báo `"Cột X tô nhiều ô"`.
     + Cột tô mờ/nghi ngờ: trả ký tự `"?"`, trạng thái `AMBIGUOUS`, ghi nhận cảnh báo.
     + Hỗ trợ đầy đủ số báo danh có số 0 ở đầu (ví dụ `"0123"`), không bị mất số 0 do ép kiểu số nguyên.
2. **Module `read_sheet.py` (Hàm đọc phiếu thống nhất)**:
   - Cung cấp hàm duy nhất `read_sheet(image_path)` để chạy trọn vẹn toàn bộ pipeline từ Giai đoạn 3 (nắn phối cảnh), Giai đoạn 4 (đọc 50 câu), đến Giai đoạn 5 (đọc SBD và Mã đề).
   - Dùng chung cho cả phiếu đáp án mẫu của giáo viên lẫn bài làm của học sinh.
   - Trả về cấu trúc dữ liệu chuẩn:
     ```python
     {
         "sbd": str,             # Chuỗi SBD (ví dụ: "1234" hoặc "????")
         "ma_de": str,           # Chuỗi Mã đề (ví dụ: "567" hoặc "???")
         "answers": list,        # Đúng 50 phần tử kết quả từng câu
         "warnings": list[str],  # Danh sách toàn bộ cảnh báo
         "file_path": str,
         "method": str,          # Phương pháp nắn ('marker' hoặc 'contour')
         "warped": np.ndarray,   # Ảnh phiếu nắn phẳng chuẩn 1055x1491
     }
     ```
   - Chế độ `--debug`: Khoanh ô được chọn trong SBD và Mã đề (xanh: hợp lệ, đỏ: MULTI, vàng: AMBIGUOUS), xuất ảnh tổng hợp toàn diện `sheet_full_{ten_goc}.png`.
3. **Kết quả kiểm thử trên 50 phiếu sạch & 50 phiếu biến dạng**:
   - **Phiếu sạch (50 phiếu)**: Đúng SBD: **50/50 (100.0%)**, Đúng Mã đề: **50/50 (100.0%)**.
   - **Phiếu biến dạng phối cảnh + xoay + nhiễu (50 phiếu)**: Đúng SBD: **50/50 (100.0%)**, Đúng Mã đề: **50/50 (100.0%)** (yêu cầu $\ge 98\%$).
   - Các ca đặc biệt (cột trống $\to$ `"?"`, cột tô đôi $\to$ `"?"` kèm cảnh báo, SBD bắt đầu bằng số 0) đều đạt 100%.
4. **Nghiệm thu ảnh thực tế**:
   - `Mẫu GV.png`: Mã đề = `"???"` (do phiếu mẫu để trống mã đề), 50/50 câu hợp lệ (`CBDACBDACBDA...`).
   - `Hs1.png`: SBD = `"1234"`, Mã đề = `"567"`, 50/50 câu hợp lệ (0 cảnh báo).
   - `Hs2.png`: SBD = `"1234"`, Mã đề = `"567"`, 27 câu hợp lệ, 12 câu trống, 11 câu nghi ngờ mờ (23 cảnh báo).

### Giai đoạn 6 – Dựng đáp án mẫu, Chấm bài học sinh & Xuất kết quả
- **Ngày**: 2026-09-29 12:45
- **Số test**: 11 (bao gồm 2 phiếu mẫu giả lập, 20 phiếu học sinh giả lập, kiểm thử can thiệp pixel và ảnh thật) | **Pass**: 11 | **Fail**: 0
- **Thời gian chạy test**: 4.53s

**Quyết định thiết kế & kết quả thực nghiệm**:
1. **Dựng đáp án chuẩn trực tiếp từ ảnh (`answer_key.py`)**:
   - Đáp án chuẩn được đọc trực tiếp từ ảnh trong `data/answer_key_images/` qua `read_sheet()`, tuyệt đối không dùng file CSV/nhập tay.
   - Kiểm định chất lượng nghiêm ngặt (`LoiDapAnMau`):
     + Mã đề phải đủ 3 chữ số, không chứa `"?"`.
     + Cả 50 câu phải là đáp án đơn hợp lệ A/B/C/D (không chấp nhận BLANK, MULTI, AMBIGUOUS).
     + Mỗi mã đề chỉ được có duy nhất 1 ảnh đáp án; phát hiện trùng lặp sẽ báo lỗi nêu rõ tên các file.
     + Cho phép `--override-key-made` để hỗ trợ trường hợp phiếu mẫu để trống mã đề (như `Mẫu GV.png` để trống mã đề, được gán `567`).
2. **Chấm bài học sinh (`scoring.py`)**:
   - Ghép bài học sinh với đáp án chuẩn CÙNG MÃ ĐỀ.
   - Mã đề không tồn tại hoặc chứa `"?"` $\to$ chuyển trạng thái `CHƯA CHẤM - [Lý do]`, vẫn lưu SBD và đáp án thô, hỗ trợ nhập tay ghi đè (`--override-made`).
   - So sánh 50 câu: ĐÚNG (+0.2 điểm) / SAI / BỎ TRỐNG / TÔ NHIỀU / NGHI NGỜ (AMBIGUOUS - gắn cờ cần xem lại).
   - Tổng điểm làm tròn 2 chữ số thập phân (`round(so_dung * 0.2, 2)`).
3. **Chứng minh đáp án đọc từ ảnh**:
   - Khi sửa trực tiếp pixel câu 5 từ 'A' sang 'C' trên ảnh mẫu giả lập `Key_999.png`, từ điển đáp án tự động cập nhật câu 5 thành 'C' và bài học sinh chọn 'C' ngay lập tức tăng từ 9.8 lên 10.0 điểm.
4. **Xuất kết quả (`export.py`)**:
   - **Excel (`outputs/ketqua.xlsx`)**: Đủ 3 sheet chuẩn `TongHop` (bảng tổng kết điểm), `ChiTiet` (tô màu xanh/đỏ/xám/cam/vàng cho từng câu), và `DapAn` (đối chiếu đáp án chuẩn theo mã đề).
   - **SQLite (`outputs/ketqua.db`)**: 4 bảng chuẩn (`dap_an_chuan`, `thi_sinh`, `bai_lam`, `chi_tiet_cau`), hỗ trợ upsert khi chạy lại mà không bị nhân đôi bản ghi.
5. **Nghiệm thu ảnh thực tế**:
   - `Mẫu GV.png`: Dựng đáp án chuẩn mã đề `567`: `CBDACBDACBDACBDCABDCBDACBDACBDCADBCBDACBDCABDCBADC`.
   - `Hs1.png`: SBD `1234`, Mã đề `567` $\to$ **50/50 câu đúng** $\to$ **10.00 điểm** (ĐÃ CHẤM).
   - `Hs2.png`: SBD `1234`, Mã đề `567` $\to$ **6 câu đúng, 21 câu sai, 12 bỏ trống, 11 nghi ngờ** $\to$ **1.20 điểm** (ĐÃ CHẤM).
   - Các file chính thức `outputs/ketqua.xlsx` và `outputs/ketqua.db` đã được xuất hoàn tất.

### Giai đoạn 7 – Tăng độ bền với ảnh chụp thực tế và Chấm hàng loạt
- **Ngày**: 2026-09-29 13:25
- **Số test**: 7 (bao gồm 64 phiếu học sinh biến dạng nặng + 2 phiếu đáp án mẫu biến dạng nặng + lô kiểm thử hỗn hợp ảnh hỏng + phát hiện trùng bài + hồi quy GĐ4, 5, 6) | **Pass**: 7 | **Fail**: 0
- **Thời gian chạy test**: 20.55s
- **Cấu hình máy tính đo kiểm thực tế**:
  + **CPU**: AMD Ryzen 5 7530U with Radeon Graphics (6 nhân, 12 luồng, xung nhịp cơ bản ~2.00 GHz, tối đa ~4.5 GHz)
  + **RAM**: 16.0 GB DDR4 (khả dụng ~14.0 GB)
  + **Ổ cứng**: SSD NVMe PCIe tốc độ cao
  + **Hệ điều hành**: Microsoft Windows 11 Home Single Language (64-bit)
  + **Môi trường**: Python 3.12.10, OpenCV 4.13.0, NumPy, pytest 9.1.1

**Quyết định thiết kế & kết quả thực nghiệm**:
1. **Kiểm tra chất lượng ảnh đầu vào (`kiem_tra_chat_luong_anh` trong `preprocess.py`)**:
   - Kiểm tra độ sáng trung bình: phát hiện ảnh quá tối (`mean < 50`) hoặc quá sáng/lóa (`mean > 235`).
   - Kiểm tra độ sắc nét bằng phương sai toán tử Laplacian (`variance < 50` cảnh báo mờ nét).
   - Kiểm tra độ phân giải tối thiểu (`300 × 300 px`).
   - Trả về danh sách cảnh báo tiếng Việt rõ ràng, giúp giáo viên nhận biết nguyên nhân ảnh chụp không đạt chuẩn.
2. **Khử bóng đổ, cân bằng sáng & Khử nhiễu (`preprocess.py`)**:
   - Khử nhiễu muối tiêu và làm mịn nhẹ nén JPEG bằng `cv2.bilateralFilter` bảo tồn biên sắc.
   - Thuật toán cân bằng sáng và loại bỏ bóng đổ bằng ước lượng nền hình thái học (Background compensation) kết hợp CLAHE.
   - Áp dụng phân ngưỡng thích nghi cục bộ (`cv2.adaptiveThreshold` với Gaussian weights) trong `bubbles.py` và `identity.py`, tính ngưỡng riêng biệt cho từng ô tròn theo vùng lân cận $41 \times 41\text{ px}$. Triệt tiêu hoàn toàn tác động của bóng đổ nửa phiếu hoặc độ sáng chênh lệch lớn giữa các vùng.
3. **Tối ưu hóa độ bền nhận diện marker góc (`detect_sheet.py`)**:
   - Chuyển `cv2.findContours` sang chế độ `cv2.RETR_LIST` thay vì `RETR_EXTERNAL`. Quyết định này giúp thuật toán trích xuất được 100% các ô marker bên trong tờ giấy ngay cả khi viền nền bàn chụp tối hơn giấy bao quanh toàn bộ khung hình.
   - Thiết lập cơ chế kiểm tra đa cấp độ: Thử adaptiveThreshold với $C = 15, 10, 8 \to$ thử Otsu trực tiếp $\to$ thử trên ảnh cân bằng sáng. Xác thực 4 marker bằng tính lồi của tứ giác, diện tích tối thiểu và kiểm tra tỉ lệ khung hình A4 ($1.05 \le \text{AR} \le 1.95$).
4. **Tự động nhận diện và sửa chiều xoay 180° bền vững (`kiem_tra_nguoc_180` trong `warp.py`)**:
   - Sử dụng phân ngưỡng thích nghi cục bộ trên ảnh đã khử nhiễu để định vị cột marker phân cách tại $x \sim 725\text{ px}$ (nửa trên khi xuôi) vs $x \sim 330\text{ px}$ (nửa dưới khi bị xoay ngược 180°).
   - Kết hợp kiểm tra mật độ timing marks giữa 2 cột câu hỏi trên ảnh nhị phân. Không còn bị đánh lừa bởi bóng đổ tối nửa trên như thuật toán đếm pixel thô trước đây.
5. **Chế độ chấm hàng loạt & Ghi log lỗi (`main.py`, `scoring.py`, `export.py`)**:
   - `--key-dir <thư_mục_đáp_án> --student-dir <thư_mục_bài_làm>`: Dựng từ điển đáp án chuẩn DUY NHẤT MỘT LẦN từ toàn bộ ảnh mẫu, sau đó duyệt chấm toàn bộ bài làm trong thư mục.
   - Xử lý lỗi an toàn: Các file rỗng, file không phải ảnh, ảnh trắng tinh, ảnh không tìm thấy phiếu đều được bắt lỗi tự động, gán trạng thái `LOI_ANH` và ghi vào sheet `Loi` trong file Excel mà không làm dừng cả lô.
   - Phát hiện và cảnh báo nghi trùng bài: Tự động gom nhóm các bài làm có cùng SBD và Mã đề, đánh dấu cờ `nghi_trung_bai: true`, đưa vào cảnh báo trên console và cột Ghi chú sheet `TongHop`.
6. **Hỗ trợ chụp trực tiếp từ webcam (`webcam.py`)**:
   - Cung cấp hàm `kiem_tra_camera()` và `chup_anh_tu_webcam()`, tích hợp tham số `--webcam` vào CLI.
   - Hiển thị khung định vị chữ nhật và hướng dẫn thao tác (SPACE: chụp, Q/ESC: hủy).
   - Nếu máy tính không có camera hoặc không mở được webcam: Báo lỗi nhẹ nhàng bằng tiếng Việt, hướng dẫn cắm lại camera hoặc dùng ảnh file thông thường mà không làm chương trình sập.
7. **Kết quả kiểm thử trên 64 phiếu biến dạng mạnh & 2 phiếu mẫu biến dạng**:
   - **Ảnh đáp án mẫu biến dạng (`Key_101.png`, `Key_202.png` nghiêng 22°, sáng 55-60%, bóng đổ nửa phiếu, nhiễu muối tiêu, JPEG Q=50)**: Đọc đúng **100.0%** cả 50/50 đáp án của cả 2 mã đề.
   - **64 phiếu học sinh biến dạng mạnh**:
     + Số phiếu làm chương trình sập: **0/64 (0.0%, đạt chỉ tiêu = 0)**.
     + Tỉ lệ đọc đúng từng câu: **99.38% (3180/3200 câu, vượt chỉ tiêu $\ge 97.0\%$)**.
     + Tỉ lệ đọc đúng cả SBD + Mã đề: **100.00% (64/64 phiếu, vượt chỉ tiêu $\ge 95.0\%$)**.
     + Thời gian xử lý trung bình: **0.157 giây/phiếu** trên ảnh biến dạng nặng, và **0.126 giây/phiếu** trên ảnh thật (vượt xa chỉ tiêu $\le 3.0\text{ giây/phiếu}$).
   - **Kiểm thử lô hỗn hợp (2 ảnh tốt, 1 file 0 byte, 1 file text, 1 ảnh trắng, 1 ảnh nhiễu)**: Lô chạy hết 6/6 file, sheet `Loi` trong Excel ghi nhận chính xác 4 file lỗi cùng nguyên nhân cụ thể.
   - **Kiểm thử hồi quy GĐ4, 5, 6**: Chạy lại toàn bộ test với `Hs1.png` (đạt 10.00 điểm, 50/50) và `Mẫu GV.png` (50/50) đều PASS 100%, chứng minh không có bất kỳ hồi quy nào.

### Giai đoạn 8 – Xây dựng giao diện người dùng bằng Tkinter
- **Ngày**: 2026-09-29 13:30
- **Số test**: 7 | **Pass**: 7 | **Fail**: 0
- **Thời gian chạy test**: 4.36s
- **Khởi chạy ứng dụng**:
  + `python -m omr.gui`
  + `python main.py --gui`

**Quyết định thiết kế & kết quả thực nghiệm**:
1. **Kiến trúc tách rời Controller và View (`OMRController` vs `OMRMainWindow`)**:
   - `OMRController`: Đóng gói toàn bộ trạng thái nghiệp vụ (quản lý đáp án chuẩn, danh sách bài làm, tiến trình chấm, sửa tay đáp án/mã đề/SBD, tính lại điểm, xuất Excel/SQLite). Controller hoàn toàn độc lập với GUI framework, cho phép kiểm thử tự động toàn diện và kiểm thử khói không cần cửa sổ hiển thị (`root.withdraw()`).
   - `OMRMainWindow`: Xây dựng bằng `tkinter` + `ttk` với theme hiện đại (`clam`), màu sắc hài hòa (`#1a365d`, `#2b6cb0`, `#276749`, `#c53030`), cỡ chữ và layout co giãn linh hoạt (`grid_rowconfigure`, `grid_columnconfigure`) tương thích mọi độ phân giải.
2. **Quy trình 3 bước trực quan mô phỏng đúng giáo viên**:
   - **Bước 1 – Đáp án mẫu**: Nút "Chọn ảnh đáp án mẫu" và "Chọn thư mục đáp án mẫu". Tự động gọi `dung_dap_an_chuan()` để trích xuất mã đề và 50 đáp án. Hiển thị bảng mã đề + 50 đáp án chuẩn. Cho phép giáo viên **xác nhận hoặc sửa tay đáp án chuẩn** nếu phát hiện sai sót trước khi chấm.
   - **Bước 2 – Bài làm học sinh**: Cung cấp 3 chế độ nạp: "Chọn ảnh lẻ", "Chọn thư mục", và "Chụp từ webcam". Tích hợp module `webcam.py`: tự động kiểm tra camera, nếu không có phần cứng thì hiển thị hộp thoại cảnh báo thân thiện và vô hiệu hóa nút an toàn mà không làm sập ứng dụng.
   - **Bước 3 – Chấm và Kết quả**:
     + Nút "Bắt đầu chấm": Chấm toàn bộ bài làm của học sinh. Xử lý đa luồng (`threading.Thread(daemon=True)`) giúp giao diện hoàn toàn không bị giật/đơ khi chấm thư mục lớn. Cập nhật `ttk.Progressbar` theo thời gian thực.
     + Bảng tổng hợp (Treeview): Liệt kê STT, Tên file, SBD, Mã đề, Số câu đúng, Sai, Trống, Điểm số, và Trạng thái.
     + Bảng chi tiết 50 câu: Khi chọn một học sinh trong bảng, hiển thị chi tiết từng câu: Số thứ tự, Đáp án HS, Đáp án chuẩn, Kết quả (Đúng/Sai/Bỏ trống/Nghi ngờ/Tô nhiều ô).
     + Khung xem ảnh kép: Hiển thị đồng thời ảnh gốc chụp từ camera/điện thoại (bên trái) và ảnh phiếu đã nắn thẳng có khoanh tròn đáp án (bên phải: Xanh lá = đúng, Đỏ = sai kèm viền đáp án chuẩn, Vàng = nghi ngờ/nhiều ô). Tự động co giãn theo kích thước khung hình giữ nguyên tỉ lệ aspect ratio.
     + Sửa tay đáp án & Mã đề: Cho phép giáo viên bấm trực tiếp vào câu có trạng thái `AMBIGUOUS` / `MULTI` hoặc ô Mã đề/SBD có dấu `?` để sửa nhanh. Hệ thống tự động gọi `tinh_diem_50_cau()` cập nhật lại điểm số, số câu đúng/sai và trạng thái tức thì.
     + Nút "Xuất Excel" và "Lưu SQLite": Xuất báo cáo trực tiếp từ giao diện với hộp thoại chọn nơi lưu file.
3. **Quản lý luồng và Thoát ứng dụng an toàn**:
   - Bắt sự kiện đóng cửa sổ (`WM_DELETE_WINDOW`): Tự động đặt cờ hủy luồng `_huy_cham = True` và giải phóng tài nguyên sạch sẽ, không để lại tiến trình ngầm (zombie threads).
4. **Kiểm thử tự động & Chụp màn hình thực tế**:
   - Kiểm thử nghiệp vụ theo kịch bản: nạp đáp án mẫu $\to$ kiểm tra bảng đáp án chuẩn $\to$ nạp bài làm $\to$ chấm ra điểm chuẩn xác; chấm khi chưa nạp đáp án mẫu $\to$ cảnh báo chuẩn mực không crash; chấm thư mục $\to$ nhận đủ số bài; sửa tay đáp án $\to$ điểm số cập nhật ngay lập tức; xuất Excel/SQLite từ giao diện; ảnh lỗi $\to$ báo lỗi an toàn.
   - Kiểm thử khói tự động: Khởi tạo GUI, mô phỏng các click nút nghiệp vụ, kiểm tra trạng thái widget thành công 100%.
   - Chụp ảnh màn hình cửa sổ thực tế bằng Windows GDI (`PrintWindow` + `GetDIBits`), lưu vĩnh viễn tại `outputs/screenshots/gui_sample.png` (275 KB, 1366 × 768 px).

### Giai đoạn 9 – Kiểm thử tổng thể, dọn dẹp, đóng gói và Chuẩn bị tài liệu nộp bài
- **Ngày**: 2026-09-29 13:45
- **Số test tổng thể**: 5 | **Pass**: 5 | **Fail**: 0
- **Thời gian chạy test**: 3.11s
- **Kiểm thử môi trường sạch (Clean venv test)**: PASS 100% (cài đặt thành công toàn bộ dependencies từ `requirements.txt`, chạy CLI `main.py --help` và đọc ảnh mẫu trơn tru).
- **Kiểm tra tĩnh (Static Code Hygiene)**: PASS 100% (0 đường dẫn tuyệt đối máy cá nhân, 0 mật khẩu/token, 100% file Python AST parse hợp lệ).

#### Bảng tổng hợp các chỉ số kỹ thuật cuối cùng của dự án:
| Tiêu chí kỹ thuật | Kết quả đạt được | Yêu cầu chuẩn | Đánh giá |
| :--- | :---: | :---: | :---: |
| **Độ chính xác đọc Đáp án mẫu** | **100.0%** (2/2 mã đề) | $\ge 99.0\%$ | Đạt xuất sắc |
| **Độ chính xác mức câu (Bài làm)** | **99.38%** (3180/3200 câu trên tập 64 phiếu biến dạng nặng)<br>**100.0%** (trên ảnh bài làm thật) | $\ge 97.0\%$ | Đạt xuất sắc |
| **Độ chính xác mức phiếu của bài làm** | **100.0%** (64/64 phiếu nắn phẳng và nhận diện thành công) | $\ge 95.0\%$ | Hoàn hảo |
| **Độ chính xác đọc SBD & Mã đề** | **100.0%** (64/64 phiếu) | $\ge 95.0\%$ | Hoàn hảo |
| **Tốc độ xử lý trung bình** | **0.126 s / phiếu** (ảnh thông thường)<br>**0.157 s / phiếu** (ảnh biến dạng nặng) | $\le 3.0$ s / phiếu | Nhanh gấp 20 lần |
| **Số ca lỗi được xử lý an toàn** | **100%** (file 0 byte, file text, ảnh trắng, ảnh cắt góc, không camera, mã đề không khớp, trùng bài) | Không sập | Đã kiểm chứng |
| **Khả năng chạy trên môi trường mới** | **100%** (venv sạch từ requirements.txt) | Chạy được | Đã kiểm chứng |

#### Bộ tài liệu hoàn chỉnh hỗ trợ nộp bài (thư mục `docs/`):
1. `docs/NOI_DUNG_BAO_CAO.md`: Dàn ý và nội dung nháp toàn diện cho báo cáo Word (Đặt vấn đề, Nghiệp vụ giáo viên, So sánh phương pháp, Chi tiết thuật toán từng bước kèm công thức toán học và số liệu thực tế, Kiến trúc module, Kết quả đo kiểm, Hạn chế & Hướng phát triển, Bảng phân công 4 thành viên).
2. `docs/NOI_DUNG_SLIDE.md`: Dàn ý 12 slide thuyết trình hoàn chỉnh, súc tích (Tiêu đề, 3-5 ý cốt lõi, gợi ý hình ảnh trực quan).
3. `docs/KICH_BAN_VIDEO.md`: Kịch bản quay video dài 7 phút 30 giây chia đều cho 4 thành viên (Nguyễn Văn A, Trần Thị B, Lê Văn C, Phạm Thị D), khớp thời lượng từng phân đoạn kèm lời thoại chi tiết và hướng dẫn quay màn hình demo luồng 3 bước.
4. `docs/CAU_HOI_ON_TAP.md`: 20 câu hỏi vấn đáp chuyên sâu bám sát mã nguồn dự án, kèm câu trả lời ngắn gọn, chuẩn xác giúp sinh viên tự tin bảo vệ đề tài.
5. `docs/LINK_VIDEO.txt`: File mẫu lưu đường link video YouTube phục vụ nộp bài.
6. `dong_goi.py`: Script tự động nén toàn bộ sản phẩm thành 1 file ZIP duy nhất theo đúng quy chuẩn E-learning (loại trừ `venv`, `tests_tmp`, `__pycache__`).



