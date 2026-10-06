"""
Package omr – Chấm phiếu trả lời trắc nghiệm từ ảnh.

Kiến trúc module:
    config.py       - Nạp và kiểm tra cấu hình từ config.json
    preprocess.py   - Tiền xử lý ảnh (grayscale, blur, ngưỡng)
    detect_sheet.py - Phát hiện biên phiếu trả lời trong ảnh
    warp.py         - Cắt và nắn phối cảnh (warpPerspective)
    bubbles.py      - Phát hiện và đọc các ô tô (bubbles)
    identity.py     - Đọc số báo danh (SBD) và mã đề
    read_sheet.py   - Đọc toàn bộ 1 phiếu (dùng chung cho đáp án mẫu & bài làm)
    answer_key.py   - Dựng bảng đáp án chuẩn từ ảnh phiếu đáp án mẫu
    grade_logic.py  - Logic chấm điểm (so sánh bài làm với đáp án)
    scoring.py      - Tổng hợp và thống kê kết quả
    export.py       - Xuất kết quả ra Excel (.xlsx) và SQLite (.db)
    gui.py          - Giao diện người dùng (Tkinter + Pillow)
"""

__version__ = "0.1.0"
