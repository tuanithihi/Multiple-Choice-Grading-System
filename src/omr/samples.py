"""
samples.py – Quản lý, liệt kê và kiểm tra tập ảnh đầu vào của dự án OMR.

Chức năng:
    - Quét các file ảnh trong thư mục (jpg, jpeg, png, bmp).
    - Đọc ảnh hỗ trợ đường dẫn Unicode (tiếng Việt).
    - Kiểm tra tính toàn vẹn của ảnh, báo file hỏng mà không làm sập chương trình.
    - Cung cấp thông tin chi tiết: kích thước (rộng x cao), số kênh màu, dung lượng.
    - Tách bạch rõ ràng giữa thư mục đáp án mẫu và thư mục bài làm học sinh.
"""

import os
from typing import Any
import cv2
import numpy as np


CAC_DUOI_ANH_HOP_LE = (".jpg", ".jpeg", ".png", ".bmp")


def doc_anh_unicode(duong_dan: str) -> np.ndarray | None:
    """
    Đọc ảnh từ file hỗ trợ đường dẫn chứa ký tự Unicode (tiếng Việt).

    Args:
        duong_dan: Đường dẫn tới file ảnh.

    Returns:
        np.ndarray nếu đọc thành công, None nếu file lỗi hoặc không đọc được.
    """
    if not os.path.isfile(duong_dan):
        return None
    try:
        du_lieu = np.fromfile(duong_dan, dtype=np.uint8)
        if du_lieu.size == 0:
            return None
        anh = cv2.imdecode(du_lieu, cv2.IMREAD_COLOR)
        return anh
    except Exception:
        return None


def kiem_tra_anh(duong_dan: str) -> dict[str, Any]:
    """
    Kiểm tra một file ảnh và trả về thông tin chi tiết.

    Args:
        duong_dan: Đường dẫn tới file ảnh.

    Returns:
        dict chứa:
            - duong_dan: đường dẫn chuẩn hóa
            - ten_file: tên file
            - ton_tai: bool
            - hop_le: bool
            - chieu_rong: int (hoặc 0)
            - chieu_cao: int (hoặc 0)
            - so_kenh: int (hoặc 0)
            - dung_luong_bytes: int
            - loi: str | None
    """
    ten_file = os.path.basename(duong_dan)
    ket_qua: dict[str, Any] = {
        "duong_dan": os.path.normpath(duong_dan),
        "ten_file": ten_file,
        "ton_tai": False,
        "hop_le": False,
        "chieu_rong": 0,
        "chieu_cao": 0,
        "so_kenh": 0,
        "dung_luong_bytes": 0,
        "loi": None,
    }

    if not os.path.exists(duong_dan):
        ket_qua["loi"] = f"File không tồn tại: {duong_dan}"
        return ket_qua

    if not os.path.isfile(duong_dan):
        ket_qua["loi"] = f"Đường dẫn không phải file: {duong_dan}"
        return ket_qua

    ket_qua["ton_tai"] = True
    ket_qua["dung_luong_bytes"] = os.path.getsize(duong_dan)

    # Đuôi file có thuộc định dạng ảnh hỗ trợ không
    if not ten_file.lower().endswith(CAC_DUOI_ANH_HOP_LE):
        ket_qua["loi"] = f"Định dạng file không được hỗ trợ: {ten_file}"
        return ket_qua

    # Đọc thử ảnh
    anh = doc_anh_unicode(duong_dan)
    if anh is None:
        ket_qua["loi"] = f"File ảnh hỏng hoặc không thể giải mã: {ten_file}"
        return ket_qua

    h, w = anh.shape[:2]
    c = anh.shape[2] if len(anh.shape) == 3 else 1
    ket_qua["hop_le"] = True
    ket_qua["chieu_rong"] = w
    ket_qua["chieu_cao"] = h
    ket_qua["so_kenh"] = c
    return ket_qua


def liet_ke_anh_thu_muc(thu_muc: str) -> list[dict[str, Any]]:
    """
    Liệt kê và kiểm tra toàn bộ file ảnh trong một thư mục.

    Args:
        thu_muc: Đường dẫn tới thư mục cần kiểm tra.

    Returns:
        Danh sách dict thông tin từng file ảnh (được sắp xếp theo tên file).
        Nếu thư mục không tồn tại, trả về danh sách rỗng.
    """
    if not os.path.isdir(thu_muc):
        return []

    danh_sach: list[dict[str, Any]] = []
    cac_file = sorted(os.listdir(thu_muc))

    for ten_file in cac_file:
        duong_dan_day_du = os.path.join(thu_muc, ten_file)
        # Bỏ qua thư mục con và file hệ thống/gitkeep
        if not os.path.isfile(duong_dan_day_du) or ten_file.startswith("."):
            continue
        if ten_file.lower().endswith(CAC_DUOI_ANH_HOP_LE):
            info = kiem_tra_anh(duong_dan_day_du)
            danh_sach.append(info)

    return danh_sach


def nap_tap_anh(thu_muc_dap_an: str, thu_muc_bai_lam: str) -> dict[str, Any]:
    """
    Nạp và kiểm tra đồng thời hai thư mục đáp án mẫu và bài làm học sinh,
    đảm bảo phân tách hoàn toàn giữa hai nguồn dữ liệu.

    Args:
        thu_muc_dap_an: Thư mục chứa ảnh đáp án mẫu.
        thu_muc_bai_lam: Thư mục chứa ảnh bài làm học sinh.

    Returns:
        dict chứa:
            - dap_an_mau: list[dict]
            - bai_lam: list[dict]
            - so_dap_an_hop_le: int
            - so_bai_lam_hop_le: int
            - so_file_hong: int
    """
    ds_dap_an = liet_ke_anh_thu_muc(thu_muc_dap_an)
    ds_bai_lam = liet_ke_anh_thu_muc(thu_muc_bai_lam)

    hop_le_da = sum(1 for a in ds_dap_an if a["hop_le"])
    hop_le_bl = sum(1 for a in ds_bai_lam if a["hop_le"])
    hong_da = sum(1 for a in ds_dap_an if not a["hop_le"])
    hong_bl = sum(1 for a in ds_bai_lam if not a["hop_le"])

    return {
        "dap_an_mau": ds_dap_an,
        "bai_lam": ds_bai_lam,
        "so_dap_an_hop_le": hop_le_da,
        "so_bai_lam_hop_le": hop_le_bl,
        "so_file_hong": hong_da + hong_bl,
    }
