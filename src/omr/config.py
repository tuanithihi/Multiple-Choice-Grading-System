"""
config.py – Nạp và kiểm tra cấu hình từ file config/config.json.

Chức năng chính:
    - Đọc file JSON cấu hình.
    - Kiểm tra đủ các khóa bắt buộc và đúng kiểu dữ liệu.
    - Cung cấp hàm tiện ích để các module khác lấy thông số.
"""

import json
import os
from typing import Any


# Đường dẫn mặc định tới file config (tính từ thư mục gốc dự án)
_MAC_DINH_DUONG_DAN = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "config", "config.json"
)

# Định nghĩa các khóa bắt buộc và kiểu dữ liệu mong đợi
# Dạng: "đường.dẫn.khóa" -> kiểu
KHOA_BAT_BUOC: dict[str, type] = {
    "anh":              dict,
    "anh.chieu_rong":   int,
    "anh.chieu_cao":    int,
    "roi_sbd":          dict,
    "roi_ma_de":        dict,
    "roi_cau_hoi":      dict,
    "roi_cau_hoi.so_khoi":      int,
    "roi_cau_hoi.cau_moi_khoi": int,
    "roi_cau_hoi.so_dap_an":    int,
    "roi_cau_hoi.khoi":         list,
    "nguong":           dict,
    "nguong.ti_le_to_min": (int, float),
    "nguong.ti_le_to_max": (int, float),
    "diem":             dict,
    "diem.tong_cau":    int,
    "diem.diem_moi_cau": (int, float),
    "diem.diem_toi_da":  (int, float),
}


def _lay_gia_tri_theo_duong_dan(du_lieu: dict, duong_dan: str) -> Any:
    """
    Lấy giá trị từ dict lồng nhau theo đường dẫn phân cách bằng dấu chấm.

    Ví dụ: _lay_gia_tri_theo_duong_dan(data, "anh.chieu_rong") -> data["anh"]["chieu_rong"]

    Raises:
        KeyError: nếu không tìm thấy khóa.
    """
    cac_khoa = duong_dan.split(".")
    hien_tai = du_lieu
    for khoa in cac_khoa:
        if not isinstance(hien_tai, dict) or khoa not in hien_tai:
            raise KeyError(f"Thiếu khóa: '{duong_dan}' (không tìm thấy '{khoa}')")
        hien_tai = hien_tai[khoa]
    return hien_tai


def kiem_tra_config(du_lieu: dict) -> list[str]:
    """
    Kiểm tra cấu hình: đủ khóa bắt buộc và đúng kiểu dữ liệu.

    Args:
        du_lieu: dict cấu hình đã đọc từ JSON.

    Returns:
        Danh sách các lỗi (chuỗi). Rỗng nếu hợp lệ.
    """
    loi: list[str] = []

    for duong_dan, kieu_mong_doi in KHOA_BAT_BUOC.items():
        try:
            gia_tri = _lay_gia_tri_theo_duong_dan(du_lieu, duong_dan)
        except KeyError as e:
            loi.append(str(e))
            continue

        # Kiểm tra kiểu dữ liệu
        if isinstance(kieu_mong_doi, tuple):
            # Cho phép nhiều kiểu (ví dụ int hoặc float)
            if not isinstance(gia_tri, kieu_mong_doi):
                loi.append(
                    f"Sai kiểu tại '{duong_dan}': cần {kieu_mong_doi}, "
                    f"nhận được {type(gia_tri).__name__}"
                )
        else:
            if not isinstance(gia_tri, kieu_mong_doi):
                loi.append(
                    f"Sai kiểu tại '{duong_dan}': cần {kieu_mong_doi.__name__}, "
                    f"nhận được {type(gia_tri).__name__}"
                )

    return loi


def nap_config(duong_dan: str | None = None) -> dict:
    """
    Nạp cấu hình từ file JSON và kiểm tra tính hợp lệ.

    Args:
        duong_dan: đường dẫn tới file config.json.
                   Nếu None, dùng đường dẫn mặc định (config/config.json).

    Returns:
        dict cấu hình đã kiểm tra.

    Raises:
        FileNotFoundError: nếu file không tồn tại.
        ValueError: nếu cấu hình thiếu khóa hoặc sai kiểu.
        json.JSONDecodeError: nếu file JSON không hợp lệ.
    """
    if duong_dan is None:
        duong_dan = os.path.normpath(_MAC_DINH_DUONG_DAN)

    if not os.path.isfile(duong_dan):
        raise FileNotFoundError(
            f"Không tìm thấy file cấu hình: {duong_dan}"
        )

    with open(duong_dan, "r", encoding="utf-8") as f:
        du_lieu = json.load(f)

    loi = kiem_tra_config(du_lieu)
    if loi:
        thong_bao = "Cấu hình không hợp lệ:\n" + "\n".join(f"  - {l}" for l in loi)
        raise ValueError(thong_bao)

    return du_lieu
