"""
read_sheet.py – Điểm kết nối toàn bộ pipeline OMR xử lý và đọc 1 phiếu trắc nghiệm.

Hàm read_sheet() là hàm DUY NHẤT dùng để đọc một phiếu thi, dùng chung cho cả
ảnh phiếu đáp án mẫu và ảnh phiếu bài làm của học sinh.

Quy trình:
    1. Đọc file ảnh an toàn (hỗ trợ Unicode tiếng Việt trên Windows).
    2. Giai đoạn 3: Phát hiện 4 góc (marker/contour), sửa chiều xoay và nắn phối cảnh về chuẩn 1055x1491 px.
    3. Giai đoạn 4: Quét lưới và quyết định đáp án cho 50 câu hỏi trắc nghiệm (A/B/C/D, BLANK, MULTI, AMBIGUOUS).
    4. Giai đoạn 5: Đọc lưới Số báo danh (SBD) và Mã đề thi theo từng cột (0-9).
    5. Tổng hợp cảnh báo (warnings) và đóng gói kết quả đầu ra.
"""

import os
from typing import Any
import cv2
import numpy as np

from omr.config import nap_config
from omr.samples import doc_anh_unicode
from omr.warp import xu_ly_va_nan_phieu
from omr.bubbles import doc_50_cau_hoi, ve_ket_qua_cau_hoi
from omr.identity import doc_sbd_va_ma_de, ve_khoanh_identity
from omr.preprocess import luu_anh_debug, kiem_tra_chat_luong_anh
from omr.grade_logic import (
    TRANG_THAI_BLANK,
    TRANG_THAI_MULTI,
    TRANG_THAI_AMBIGUOUS,
)


def read_sheet(
    image_path: str,
    config: dict | None = None,
    debug: bool = False,
    thu_muc_debug: str = "outputs/debug"
) -> dict[str, Any]:
    """
    Đọc trọn vẹn 1 phiếu trả lời trắc nghiệm từ đường dẫn file ảnh.

    Args:
        image_path: Đường dẫn tới file ảnh phiếu (hỗ trợ đường dẫn tiếng Việt).
        config: Dict cấu hình hệ thống (nếu None sẽ tự nạp từ config/config.json).
        debug: Nếu True, xuất ảnh trực quan hóa các bước ra thư mục debug.
        thu_muc_debug: Đường dẫn thư mục lưu ảnh debug (mặc định: outputs/debug).

    Returns:
        Dict chứa đầy đủ thông tin phiếu:
            - 'sbd': Chuỗi Số báo danh (vd: "1234", hoặc "????" nếu không tô).
            - 'ma_de': Chuỗi Mã đề thi (vd: "567", hoặc "???" nếu không tô).
            - 'answers': Danh sách đúng 50 phần tử kết quả từng câu hỏi.
            - 'warnings': Danh sách các cảnh báo (SBD/Mã đề lỗi, câu hỏi MULTI, AMBIGUOUS, BLANK, ảnh mờ/tối).
            - 'file_path': Đường dẫn file ảnh gốc.
            - 'method': Phương pháp nắn phối cảnh đã dùng ('marker' hoặc 'contour').
            - 'warped': Ảnh nắn phẳng kích thước chuẩn.
    """
    if config is None:
        config = nap_config()

    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Không tìm thấy file ảnh: {image_path}")

    # 1. Đọc ảnh (hỗ trợ Unicode tiếng Việt)
    anh_goc = doc_anh_unicode(image_path)
    if anh_goc is None:
        raise ValueError(f"Không thể đọc file ảnh (file hỏng hoặc định dạng không hỗ trợ): {image_path}")

    # 1.1 Kiểm tra chất lượng ảnh đầu vào (quá tối, quá mờ nét, độ phân giải)
    hop_le_ql, warnings_ql = kiem_tra_chat_luong_anh(anh_goc)
    if not hop_le_ql:
        raise ValueError(f"Ảnh không đạt chất lượng tối thiểu: {'; '.join(warnings_ql)}")

    ten_goc = os.path.splitext(os.path.basename(image_path))[0]

    # 2. Giai đoạn 3: Phát hiện biên, sửa chiều xoay và nắn phối cảnh
    warped, pts, method = xu_ly_va_nan_phieu(
        anh_goc,
        config=config,
        debug=debug,
        ten_debug=f"read_{ten_goc}",
        thu_muc_debug=thu_muc_debug
    )

    # 3. Giai đoạn 4: Đọc 50 câu hỏi trắc nghiệm (có tự hiệu chỉnh ngưỡng thích nghi)
    answers = doc_50_cau_hoi(
        warped,
        config=config,
        debug=debug,
        ten_debug=f"read_{ten_goc}",
        thu_muc_debug=thu_muc_debug
    )

    # Lấy ngưỡng thích nghi đã hiệu chỉnh từ 50 câu để áp dụng cho SBD / Mã đề
    nguong_adapted = answers[0].get("nguong_su_dung") if answers else None

    # 4. Giai đoạn 5: Đọc Số báo danh và Mã đề
    id_result = doc_sbd_va_ma_de(
        warped,
        config=config,
        debug=debug,
        ten_debug=f"read_{ten_goc}",
        thu_muc_debug=thu_muc_debug,
        nguong_tuy_chinh=nguong_adapted
    )

    sbd = id_result["sbd"]
    ma_de = id_result["ma_de"]
    warnings: list[str] = list(warnings_ql) + list(id_result.get("warnings", []))

    # 5. Tổng hợp cảnh báo từ 50 câu hỏi
    for item in answers:
        q = item["cau"]
        st = item["trang_thai"]
        if st == TRANG_THAI_MULTI:
            warnings.append(f"Câu {q}: Tô nhiều ô (MULTI)")
        elif st == TRANG_THAI_AMBIGUOUS:
            warnings.append(f"Câu {q}: Tô mờ/nghi ngờ sát ngưỡng (AMBIGUOUS)")
        elif st == TRANG_THAI_BLANK:
            warnings.append(f"Câu {q}: Bỏ trống (BLANK)")

    # 6. Nếu bật debug, tạo thêm 1 ảnh tổng hợp toàn diện (full annotated)
    if debug:
        vis = ve_ket_qua_cau_hoi(warped, answers, config)
        vis = ve_khoanh_identity(vis, id_result, config)
        # Ghi thông tin tổng quát ở góc trên phiếu
        cv2.putText(
            vis,
            f"FILE: {ten_goc} | SBD: {sbd} | MD: {ma_de} | METHOD: {method}",
            (60, 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 200),
            2
        )
        luu_anh_debug(vis, f"sheet_full_{ten_goc}.png", thu_muc_debug)

    return {
        "sbd": sbd,
        "ma_de": ma_de,
        "answers": answers,
        "warnings": warnings,
        "file_path": image_path,
        "method": method,
        "warped": warped,
        "chi_tiet_sbd": id_result.get("chi_tiet_sbd", []),
        "chi_tiet_ma_de": id_result.get("chi_tiet_ma_de", []),
    }
