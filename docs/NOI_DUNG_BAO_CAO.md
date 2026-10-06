# BÁO CÁO KỸ THUẬT ĐỀ TÀI BÀI TẬP NHÓM
## ĐỀ TÀI 19: HỆ THỐNG CHẤM PHIẾU TRẢ LỜI TRẮC NGHIỆM TỰ ĐỘNG TỪ ẢNH CHỤP (MẪU THPT 50 CÂU)

---

### MỤC LỤC
1. [GIỚI THIỆU ĐỀ TÀI VÀ BÀI TOÁN NGHIỆP VỤ](#1-giới-thiệu-đề-tài-và-bài-toán-nghiệp-vụ)
2. [TỔNG QUAN CÁC PHƯƠNG PHÁP OMR HIỆN CÓ](#2-tổng-quan-các-phương-pháp-omr-hiện-có)
3. [KIẾN TRÚC VÀ THUẬT TOÁN HỆ THỐNG](#3-kiến-trúc-và-thuật-toán-hệ-thống)
4. [THIẾT KẾ HỆ THỐNG VÀ CẤU TRÚC MODULE](#4-thiết-kế-hệ-thống-và-cấu-trúc-module)
5. [KẾT QUẢ THỰC NGHIỆM VÀ ĐÁNH GIÁ](#5-kết-quả-thực-nghiệm-và-đánh-giá)
6. [HẠN CHẾ VÀ HƯỚNG PHÁT TRIỂN](#6-hạn-chế-và-hướng-phát-triển)
7. [PHÂN CÔNG CÔNG VIỆC VÀ TỰ ĐÁNH GIÁ ĐIỂM](#7-phân-công-công-việc-và-tự-đánh-giá-điểm)

---

### 1. GIỚI THIỆU ĐỀ TÀI VÀ BÀI TOÁN NGHIỆP VỤ

#### 1.1. Đặt vấn đề và Ý nghĩa thực tiễn
Trong các kỳ thi THPT Quốc gia và kiểm tra định kỳ tại các trường phổ thông Việt Nam, hình thức thi trắc nghiệm khách quan với mẫu phiếu 50 câu được áp dụng rộng rãi. Việc chấm thi bằng máy quét OMR (Optical Mark Recognition) chuyên dụng đem lại độ chính xác cao nhưng chi phí phần cứng đắt đỏ, đòi hỏi phiếu thi phẳng phiu và bảo trì định kỳ. 

Mục tiêu của đề tài là xây dựng một hệ thống phần mềm thị giác máy tính mã nguồn mở, hoạt động ổn định trên máy tính cá nhân thông thường. Phần mềm cho phép giáo viên sử dụng **ảnh chụp từ điện thoại di động hoặc webcam** để tự động chấm điểm bài làm của học sinh một cách nhanh chóng, chính xác và minh bạch.

#### 1.2. Bối cảnh nghiệp vụ cốt lõi
Quy trình nghiệp vụ của hệ thống mô phỏng chính xác và tự nhiên quy trình làm việc của giáo viên:
1. **Nguồn đáp án chuẩn (Phiếu đáp án mẫu)**: Giáo viên tô một phiếu đáp án chuẩn cho mỗi mã đề thi (tương tự như học sinh làm bài). Hệ thống sử dụng chính pipeline thị giác máy tính để đọc ảnh phiếu đáp án mẫu, trích xuất Mã đề và 50 đáp án chuẩn. **Tuyệt đối không bắt giáo viên phải nhập tay đáp án** vào file cấu hình.
2. **Ảnh bài làm học sinh**: Giáo viên chụp ảnh phiếu trả lời của học sinh (bằng điện thoại hoặc webcam) trong nhiều điều kiện thực tế (ánh sáng không đều, bóng đổ, nghiêng góc, xoay).
3. **Chấm thi tự động**: Hệ thống đọc Số báo danh (SBD), Mã đề và 50 câu trả lời của từng học sinh, tự động ghép với đáp án chuẩn có cùng Mã đề, so sánh từng câu và tính điểm theo thang 10.
4. **Đối chiếu và Xuất báo cáo**: Giao diện cung cấp ảnh kép đối chiếu (ảnh gốc và ảnh nắn kèm khoanh vùng đáp án), cho phép sửa tay các câu nghi ngờ hoặc sửa mã đề khi cần, sau đó xuất bảng điểm tổng hợp ra định dạng Excel (.xlsx đa sheet) và cơ sở dữ liệu SQLite (.db).

```
                      +-----------------------------+
                      | Ảnh Phiếu Đáp Án Mẫu (GV)   |
                      +--------------+--------------+
                                     |
                                     v
                          [ Pipeline OMR Đọc Phiếu ]
                                     |
                                     v
                       { Từ điển Đáp án Chuẩn Mã Đề }
                                     |
  +---------------------------+      |
  | Ảnh Bài Làm Học Sinh (HS) |      |
  +-------------+-------------+      |
                |                    |
                v                    |
     [ Pipeline OMR Đọc Phiếu ]      |
                |                    |
  { SBD, Mã Đề, 50 Lựa Chọn }        |
                |                    |
                +----------> [ So Khớp & Chấm Điểm ] <----------+
                                     |
                                     v
                   +-----------------+-----------------+
                   |                                   |
                   v                                   v
          [ Báo Cáo Excel ]                   [ CSDL SQLite ]
        (TongHop, ChiTiet, DapAn)        (dap_an_chuan, thi_sinh, bai_lam)
```

---

### 2. TỔNG QUAN CÁC PHƯƠNG PHÁP OMR HIỆN CÓ

| Tiêu chí | Máy quét phần cứng chuyên dụng | Xử lý ảnh Cổ điển & Marker (Đề tài lựa chọn) | Học sâu / Object Detection (YOLO, Faster R-CNN) |
| :--- | :--- | :--- | :--- |
| **Độ chính xác** | Rất cao (> 99.9%) | Cao (99.4% - 100%) khi nắn chuẩn phối cảnh | Cao (95% - 98%) nhưng phụ thuộc dataset gán nhãn |
| **Yêu cầu phần cứng** | Máy quét chuyên dụng (hàng chục triệu đồng) | CPU thông thường, chạy được trên laptop cũ, không cần GPU | Yêu cầu GPU mạnh để huấn luyện hoặc suy luận |
| **Tính linh hoạt** | Rất thấp (chỉ chấp nhận giấy phẳng, đúng khổ) | Rất cao: Tự động nắn nghiêng, xoay 180°, khử bóng đổ | Linh hoạt với biến dạng nhưng khó đạt định vị chính xác tới từng pixel |
| **Khả năng giải thích** | Hộp đen của nhà sản xuất | **100% rõ ràng, có công thức toán học và ngưỡng minh bạch** | Hộp đen mạng nơ-ron, khó xác định vì sao nhận nhầm |
| **Chi phí triển khai** | Rất đắt | **0 đồng (Mã nguồn mở, thư viện chuẩn Python)** | Tốn tài nguyên và thời gian gán nhãn hàng nghìn ảnh |

**Lý do lựa chọn phương pháp xử lý ảnh kết hợp Marker định vị**:
- Tận dụng cấu trúc hình học chuẩn của phiếu trắc nghiệm Bộ GD&ĐT (4 ô vuông định vị màu đen tại 4 góc).
- Đạt tốc độ xử lý vượt trội (**~0.15 giây/phiếu** trên CPU), không phụ thuộc GPU.
- Khả năng kiểm tra và can thiệp trực quan: Giáo viên có thể nhìn rõ ảnh nhị phân và mặt nạ tính toán.

---

### 3. KIẾN TRÚC VÀ THUẬT TOÁN HỆ THỐNG

#### 3.1. Tiền xử lý ảnh (Preprocessing)
1. **Khử nhiễu bảo toàn biên**: Sử dụng bộ lọc song phương `cv2.bilateralFilter(src, d=7, sigmaColor=50, sigmaSpace=50)`. Khác với Gaussian Blur thông thường làm mờ cả viền ô tròn, Bilateral Filter làm mịn nhiễu bề mặt giấy nhưng giữ lại độ sắc nét của viền ô và nét chì.
2. **Cân bằng sáng cục bộ và Khử bóng đổ**:
   - Ước lượng nền bằng phép mở hình thái học (Morphological Opening) với phần tử cấu trúc lớn ($ksize = 31 \times 31$):
     $$\text{Background} = \text{Opening}(I) = (I \ominus B) \oplus B$$
   - Ảnh chuẩn hóa độ sáng:
     $$I_{\text{norm}} = \frac{I}{\text{Background} + \epsilon} \times 255$$
   - Áp dụng CLAHE (Contrast Limited Adaptive Histogram Equalization) với `clipLimit=2.0, tileGridSize=(8, 8)` giúp tăng độ tương phản rõ rệt giữa nét chì và nền giấy.

#### 3.2. Phát hiện biên và Nắn phối cảnh (Warp Perspective)
Hệ thống sử dụng chiến lược phát hiện 2 lớp bền vững:
- **Lớp 1 (Ưu tiên)**: Tìm 4 ô vuông đen (Corner Markers) ở 4 góc phiếu:
  - Phân ngưỡng thích nghi cục bộ `cv2.adaptiveThreshold` ($C = 10$, $ksize = 25$).
  - Trích xuất contour bằng `cv2.RETR_LIST` (cho phép tìm thấy marker ngay cả khi ảnh có nền bàn tối bao quanh).
  - Lọc marker dựa trên tiêu chí hình học: Tỉ lệ khung hình $0.65 \le \frac{w}{h} \le 1.55$, diện tích $S \in [150, 4000]\text{ px}^2$, độ đặc $\text{Extent} = \frac{\text{Area}}{w \times h} \ge 0.65$.
- **Lớp 2 (Dự phòng)**: Tìm tứ giác giấy thi bằng Canny Edge + `cv2.approxPolyDP` với điều kiện diện tích bao phủ $> 20\%$ diện tích ảnh và tỉ lệ khung hình gần chuẩn A4.

**Sắp xếp 4 đỉnh và Biến đổi phối cảnh**:
- Sắp xếp 4 điểm theo thứ tự cố định: Trên-Trái ($TL$), Trên-Phải ($TR$), Dưới-Phải ($BR$), Dưới-Trái ($BL$).
- Áp dụng ma trận biến đổi phối cảnh $3 \times 3$ đưa ảnh về kích thước chuẩn $W = 1055\text{ px}, H = 1491\text{ px}$:
  $$\begin{bmatrix} x' \\ y' \\ 1 \end{bmatrix} \sim M \begin{bmatrix} x \\ y \\ 1 \end{bmatrix}, \quad M = \text{getPerspectiveTransform}(\text{src\_pts}, \text{dst\_pts})$$

**Tự động nhận diện và sửa chiều xoay 180°**:
Phiếu thi THPT có 2 ô định vị phụ tại cột giữa ($x \sim 720\text{ px}$) ở nửa trên tờ phiếu. Thuật toán kiểm tra mật độ điểm đen tại nửa trên so với nửa dưới. Nếu phát hiện phiếu bị lộn ngược 180°, hàm tự động xoay `cv2.rotate(warped, cv2.ROTATE_180)` đưa phiếu về đúng chiều xuôi.

#### 3.3. Phân ngưỡng và Đọc các ô tròn (Bubbles)
1. **Phân ngưỡng thích nghi theo vùng**:
   Áp dụng `cv2.adaptiveThreshold` với $ksize = 41\text{ px}$ dạng đảo (INV) cho từng khối câu hỏi. Nét chì/mực biến thành màu trắng ($255$), nền giấy thành đen ($0$). Phân ngưỡng cục bộ triệt tiêu 100% hiện tượng bóng đổ nghiêng trên tờ giấy.
2. **Mặt nạ hình tròn nội tiếp (Circular Mask)**:
   Để tránh nhầm lẫn giữa nét tô của thí sinh và viền mực in sẵn của ô tròn, hệ thống tạo mặt nạ hình tròn nội tiếp bán kính $R = 8\text{ px}$ (trong khi viền in có bán kính $R_{\text{in}} \approx 11\text{ px}$):
   $$\text{Mask}(u, v) = \begin{cases} 1 & \text{nếu } (u - x_c)^2 + (v - y_c)^2 \le R^2 \\ 0 & \text{ngược lại} \end{cases}$$
3. **Công thức tính tỉ lệ tô (Fill Ratio)**:
   $$\text{fill\_ratio} = \frac{\sum_{(u, v) \in \text{Mask}} I_{\text{bin}}(u, v)}{255 \times \text{Area}(\text{Mask})}, \quad \text{với } \text{Area}(\text{Mask}) = 197\text{ pixels}$$

#### 3.4. Logic quyết định đáp án (Grade Logic)
Với 4 ô tròn tương ứng với A, B, C, D của mỗi câu:
- Gọi $r_{\max}$ là fill_ratio lớn nhất, $r_2$ là fill_ratio lớn thứ nhì.
- **Quy tắc phân loại**:
  - Nếu số ô có $r \ge 0.38$ lớn hơn hoặc bằng 2: Kết luận $\to \mathbf{MULTI}$ (Tô nhiều ô, 0 điểm).
  - Nếu tất cả 4 ô đều có $r < 0.24$: Kết luận $\to \mathbf{BLANK}$ (Bỏ trống, 0 điểm).
  - Nếu $r_{\max} \ge 0.38$ và khoảng chênh lệch $\Delta = r_{\max} - r_2 \ge 0.10$: Kết luận $\to \mathbf{H\text{Ợ}P\_L\text{Ệ}}$ (chọn đáp án của ô $r_{\max}$).
  - Các trường hợp còn lại ($0.24 \le r_{\max} < 0.38$ hoặc $\Delta < 0.10$): Kết luận $\to \mathbf{AMBIGUOUS}$ (Nghi ngờ do tẩy không sạch hoặc tô quá mờ, cờ cảnh báo giáo viên xem lại).

#### 3.5. Đọc Số báo danh (SBD) và Mã đề
- Khối SBD (4 cột, mỗi cột 10 hàng 0–9) và Khối Mã đề (3 cột, mỗi cột 10 hàng 0–9).
- Duyệt theo từng cột $c$, tìm hàng $r^*$ có fill_ratio cao nhất:
  $$r^*(c) = \arg\max_{r \in [0, 9]} \text{fill\_ratio}(c, r)$$
- Nếu $\text{fill\_ratio}(c, r^*) \ge 0.38$: Chữ số hợp lệ là $r^*$.
- Nếu không có hàng nào đạt ngưỡng hoặc có 2 hàng cùng vượt ngưỡng: Gán ký tự cảnh báo $\mathbf{?}$.

#### 3.6. Công thức chấm điểm
Mỗi câu trắc nghiệm được tính điểm độc lập:
$$\text{Điểm} = \text{Số câu đúng} \times \frac{10.0}{50} = \text{Số câu đúng} \times 0.20$$

---

### 4. THIẾT KẾ HỆ THỐNG VÀ CẤU TRÚC MODULE

Dự án được tổ chức theo kiến trúc phân tầng sạch sẽ:

```
omr_project/
├── config/
│   └── config.json          # Toàn bộ tham số tọa độ ROI, ngưỡng và bước nhảy
├── data/
│   ├── answer_key_images/   # Ảnh phiếu đáp án mẫu của giáo viên
│   └── student_images/      # Ảnh chụp bài làm của học sinh
├── docs/                    # Tài liệu kỹ thuật, slide, kịch bản video
├── outputs/                 # Bảng điểm Excel, CSDL SQLite, ảnh debug, ảnh chụp GUI
│   ├── screenshots/
│   │   └── gui_sample.png   # Ảnh chụp giao diện thực tế của hệ thống
│   ├── ketqua.xlsx          # Báo cáo Excel 3 sheet chính thức
│   └── ketqua.db            # Cơ sở dữ liệu SQLite 4 bảng
├── src/
│   └── omr/
│       ├── __init__.py      # Khai báo package
│       ├── config.py        # Quản lý nạp và kiểm tra tính toàn vẹn cấu hình
│       ├── samples.py       # Nạp ảnh Unicode tiếng Việt an toàn
│       ├── preprocess.py    # Tiền xử lý, kiểm tra chất lượng ảnh, khử bóng đổ
│       ├── detect_sheet.py  # Phát hiện 4 marker góc và biên phiếu
│       ├── warp.py          # Nắn phối cảnh, xoay ngược 180°
│       ├── bubbles.py       # Trích xuất và tính tỉ lệ tô ô tròn
│       ├── identity.py      # Đọc khối Số báo danh và Mã đề thi
│       ├── grade_logic.py   # Phân loại HOP_LE, BLANK, MULTI, AMBIGUOUS
│       ├── read_sheet.py    # Pipeline đọc toàn diện 1 phiếu
│       ├── answer_key.py    # Dựng từ điển đáp án chuẩn từ ảnh mẫu
│       ├── scoring.py       # Chấm điểm, ghép mã đề, phát hiện trùng bài
│       ├── export.py        # Xuất dữ liệu ra Excel và SQLite
│       ├── webcam.py        # Hỗ trợ chụp trực tiếp từ webcam/camera
│       └── gui.py           # Giao diện đồ họa Tkinter (OMRController & View)
├── main.py                  # Điểm khởi chạy CLI và GUI
├── requirements.txt         # Danh mục thư viện phụ thuộc
└── PROGRESS.md              # Nhật ký kiểm thử qua từng giai đoạn
```

---

### 5. KẾT QUẢ THỰC NGHIỆM VÀ ĐÁNH GIÁ

Hệ thống đã trải qua 9 giai đoạn kiểm thử toàn diện, đặc biệt là bài kiểm tra độ bền tại Giai đoạn 7 với **64 phiếu biến dạng nặng** (nghiêng phối cảnh $22^\circ$, bóng đổ $50\%$ diện tích phiếu, độ sáng giảm $45\%$, nhiễu muối tiêu, nén JPEG $Q=50$):

| Chỉ số đánh giá | Kết quả thực nghiệm | Yêu cầu chuẩn | Đánh giá |
| :--- | :---: | :---: | :---: |
| **Độ chính xác đọc Đáp án mẫu** | **100.0%** (2/2 mã đề) | $\ge 99.0\%$ | Vượt xuất sắc |
| **Độ chính xác đọc câu (Bài làm)** | **99.38%** (3180/3200 câu) | $\ge 97.0\%$ | Vượt xuất sắc |
| **Độ chính xác đọc SBD & Mã đề** | **100.0%** (64/64 phiếu) | $\ge 95.0\%$ | Hoàn hảo |
| **Số phiếu làm chương trình sập** | **0 / 64 (0.0%)** | 0% | Tuyệt đối an toàn |
| **Tốc độ xử lý trung bình** | **0.126 s / phiếu** (ảnh thường)<br>**0.157 s / phiếu** (biến dạng) | $\le 3.0$ s / phiếu | Nhanh gấp 20 lần |
| **Xử lý ngoại lệ an toàn** | 100% (file 0 byte, file text, ảnh trắng, ảnh cắt góc, không camera) | Không sập | Đã kiểm chứng |

**Đối chiếu kết quả ảnh thực tế**:
- `Mẫu GV.png`: Trích xuất thành công 50 đáp án chuẩn mã đề `567`.
- `Hs1.png` (SBD: `1234`, Mã đề: `567`): Đạt **50/50 câu đúng $\to$ 10.00 điểm**.
- `Hs2.png` (SBD: `1234`, Mã đề: `567`): Đạt **6 câu đúng, 22 câu sai, 11 bỏ trống, 11 nghi ngờ $\to$ 1.20 điểm**.
- Hệ thống tự động cảnh báo **Nghi trùng bài** khi phát hiện 2 bài thi có cùng SBD và Mã đề.

---

### 6. HẠN CHẾ VÀ HƯỚNG PHÁT TRIỂN

#### 6.1. Hạn chế hiện tại
- Yêu cầu ảnh chụp phải chứa tương đối đầy đủ 4 góc phiếu để nhận diện marker. Nếu bị rách mất cả 4 góc, hệ thống sẽ từ chối và báo lỗi ảnh.
- Chưa tích hợp tính năng nhận diện chữ viết tay (OCR) đối với tên họ học sinh (chỉ đọc SBD tô tròn).

#### 6.2. Hướng phát triển
- Tích hợp thêm mạng nơ-ron MobileNet nhẹ để phát hiện góc phiếu khi cả 4 marker bị rách hoặc che khuất.
- Xây dựng ứng dụng di động (Flutter / React Native) đồng bộ trực tiếp dữ liệu với máy chủ trường học qua REST API.

---

### 7. PHÂN CÔNG CÔNG VIỆC VÀ TỰ ĐÁNH GIÁ ĐIỂM

| STT | Thành viên | Nhiệm vụ chính phụ trách | Tự đánh giá điểm |
| :---: | :--- | :--- | :---: |
| 1 | **Nguyễn Văn A** | Trưởng nhóm; Thiết kế kiến trúc tổng thể, Thuật toán nắn phối cảnh `warp.py`, Phát hiện marker `detect_sheet.py`, Tự động xoay 180°. | /10 |
| 2 | **Trần Thị B** | Nghiên cứu thuật toán phân ngưỡng `bubbles.py`, Logic nhận diện ô tô `grade_logic.py`, Xử lý Số báo danh & Mã đề `identity.py`. | /10 |
| 3 | **Lê Văn C** | Thiết kế quy trình dựng đáp án mẫu `answer_key.py`, Thuật toán chấm điểm `scoring.py`, Xuất báo cáo Excel đa sheet & CSDL SQLite `export.py`. | /10 |
| 4 | **Phạm Thị D** | Xây dựng giao diện Tkinter `gui.py`, Kiến trúc đa luồng (threading), Tích hợp module Webcam `webcam.py`, Soạn thảo tài liệu và kịch bản video. | /10 |
