# Chấm phiếu trả lời trắc nghiệm từ ảnh (mẫu THPT 50 câu)

> **Đề tài 19** – Bài tập nhóm môn Thị giác máy tính

## Mô tả đề tài

Chương trình tự động chấm bài trắc nghiệm 50 câu (4 đáp án A/B/C/D) từ ảnh chụp
phiếu trả lời, dùng kỹ thuật **xử lý ảnh cổ điển** (OpenCV).

### Luồng hoạt động

```
┌─────────────────────────────┐     ┌─────────────────────────────┐
│  Ảnh phiếu ĐÁP ÁN MẪU     │     │  Ảnh phiếu BÀI LÀM         │
│  (1 ảnh / mã đề)           │     │  (1 ảnh / học sinh)         │
│  data/answer_key_images/    │     │  data/student_images/       │
└──────────┬──────────────────┘     └──────────┬──────────────────┘
           │                                   │
           ▼                                   ▼
    ┌──────────────────────────────────────────────────┐
    │        CÙNG MỘT PIPELINE ĐỌC PHIẾU              │
    │  grayscale → blur → Canny → findContours →       │
    │  warpPerspective → tách ROI → đếm pixel từng ô   │
    └──────────┬───────────────────────┬───────────────┘
               │                       │
               ▼                       ▼
     Đáp án chuẩn (theo mã đề)    SBD + Mã đề + 50 câu
               │                       │
               └───────┬───────────────┘
                       ▼
              So sánh từng câu (cùng mã đề)
                       │
                       ▼
              Tính điểm (0.2 đ/câu × 50 = 10 đ)
                       │
               ┌───────┴───────┐
               ▼               ▼
          Excel (.xlsx)   SQLite (.db)
```

## Cấu trúc thư mục

```
omr_project/
├── main.py                    # Điểm vào chương trình (CLI)
├── requirements.txt           # Thư viện cần cài
├── README.md                  # File này
├── PROGRESS.md                # Nhật ký tiến độ
├── .gitignore
│
├── src/omr/                   # Mã nguồn chính
│   ├── __init__.py
│   ├── config.py              # Nạp & kiểm tra cấu hình
│   ├── preprocess.py          # Tiền xử lý ảnh
│   ├── detect_sheet.py        # Phát hiện biên phiếu
│   ├── warp.py                # Cắt & nắn phối cảnh
│   ├── bubbles.py             # Phát hiện & đọc ô tô
│   ├── identity.py            # Đọc SBD, mã đề
│   ├── read_sheet.py          # Đọc 1 phiếu (dùng chung)
│   ├── answer_key.py          # Dựng đáp án chuẩn từ ảnh mẫu
│   ├── grade_logic.py         # Logic chấm điểm
│   ├── scoring.py             # Tổng hợp & thống kê
│   ├── export.py              # Xuất Excel / SQLite
│   └── gui.py                 # Giao diện Tkinter
│
├── config/
│   └── config.json            # Thông số bố cục phiếu
│
├── data/
│   ├── answer_key_images/     # Ảnh phiếu đáp án mẫu (thêm sau)
│   └── student_images/        # Ảnh bài làm học sinh (thêm sau)
│
├── outputs/                   # Kết quả: Excel, SQLite, ảnh debug
│   └── debug/                 # Ảnh trung gian khi chạy --debug
│
├── docs/                      # Tài liệu hỗ trợ báo cáo
│
└── tests_tmp/                 # Kiểm thử tạm (xóa sau mỗi giai đoạn)
```

## Cài đặt

### 1. Cài Python 3.10+

- **Windows**: Tải từ [python.org](https://www.python.org/downloads/), nhớ chọn
  "Add Python to PATH" khi cài.
- **macOS**: `brew install python@3.12`
- **Linux (Ubuntu)**: `sudo apt install python3 python3-venv python3-pip`

### 2. Tạo môi trường ảo

```bash
# Windows (PowerShell)
cd omr_project
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS / Linux
cd omr_project
python3 -m venv venv
source venv/bin/activate
```

### 3. Cài thư viện

```bash
pip install -r requirements.txt
```

### 4. Thêm ảnh (làm ở bước sau)

- Copy ảnh phiếu **đáp án mẫu** vào `data/answer_key_images/`
  (mỗi mã đề 1 ảnh, ví dụ: `de_101.jpg`, `de_102.jpg`)
- Copy ảnh **bài làm của học sinh** vào `data/student_images/`
  (ví dụ: `hs_001.jpg`, `hs_002.jpg`)

## Cách chạy

```bash
# Xem hướng dẫn
python main.py --help

# Chấm 1 ảnh bài làm
python main.py --student-image data/student_images/hs_001.jpg

# Chấm cả thư mục bài làm, xuất Excel
python main.py --student-dir data/student_images --out-excel outputs/ketqua.xlsx

# Chấm cả thư mục, xuất cả Excel và SQLite, bật debug
python main.py --student-dir data/student_images \
    --out-excel outputs/ketqua.xlsx \
    --out-db outputs/ketqua.db \
    --debug

# Chỉ định thư mục đáp án mẫu khác
python main.py --key-dir data/answer_key_images \
    --student-dir data/student_images \
    --out-excel outputs/ketqua.xlsx
```

## Ghi chú

- Đáp án chuẩn được **đọc từ ảnh phiếu đáp án mẫu**, KHÔNG nhập tay bằng CSV/JSON.
- Ảnh đáp án mẫu và ảnh bài làm dùng **cùng một hàm đọc phiếu** (`read_sheet.py`).
- Hỗ trợ nhiều mã đề: chương trình tự ghép bài làm với đáp án cùng mã đề.
