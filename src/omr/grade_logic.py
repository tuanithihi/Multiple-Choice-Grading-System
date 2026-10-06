"""
grade_logic.py – Logic phân loại và quyết định đáp án cho từng câu hỏi OMR.

Quy tắc quyết định cho từng câu từ 4 giá trị fill_ratio [A, B, C, D]:
    - Đúng 1 ô có fill_ratio >= ngưỡng_min và chênh lệch rõ rệt so với ô thứ 2 -> Lựa chọn đáp án đó.
    - Không ô nào đạt ngưỡng_ambiguous -> "BLANK" (bỏ trống).
    - Có 2 ô trở lên cùng vượt ngưỡng_min -> "MULTI" (tô nhiều ô).
    - Trường hợp sát ngưỡng (ô cao nhất nằm giữa ambiguous và min, hoặc chênh lệch 2 ô đầu quá nhỏ)
      -> "AMBIGUOUS" (nghi ngờ, đánh dấu để kiểm tra lại).
"""

from typing import Any
import numpy as np
from omr.config import nap_config


TRANG_THAI_HOP_LE = "HOP_LE"
TRANG_THAI_BLANK = "BLANK"
TRANG_THAI_MULTI = "MULTI"
TRANG_THAI_AMBIGUOUS = "AMBIGUOUS"


def tu_hieu_chinh_nguong_phieu(
    tat_ca_fill_ratios: list[float],
    config: dict | None = None
) -> dict[str, float]:
    """
    Tự hiệu chỉnh ngưỡng tô (adaptive thresholding) theo phân bố fill_ratio của toàn bộ phiếu:
        - Trên phiếu trắc nghiệm 50 câu (200 ô): ~75% là ô trống, ~25% là ô được tô.
        - Phân tích phân vị để ước lượng cụm ô trống (empty cluster) và cụm ô tô (filled cluster).
        - Tính toán động ngưỡng tối thiểu (t_min), ngưỡng nghi ngờ (t_amb), và độ chênh lệch (diff_min)
          phù hợp với độ đậm nhạt của nét chì/bút trên riêng phiếu đó.

    Args:
        tat_ca_fill_ratios: Danh sách tất cả tỉ lệ tô thu thập từ các ô trên phiếu.
        config: Dict cấu hình hệ thống.

    Returns:
        dict: Chứa 'fill_ratio_min', 'fill_ratio_ambiguous', 'fill_ratio_diff_min', 'da_hieu_chinh' (bool).
    """
    if config is None:
        config = nap_config()

    nguong_cfg = config.get("nguong", {})
    t_min_def = float(nguong_cfg.get("fill_ratio_min", nguong_cfg.get("ti_le_to_min", 0.38)))
    t_amb_def = float(nguong_cfg.get("fill_ratio_ambiguous", nguong_cfg.get("ti_le_to_ambiguous", 0.24)))
    diff_min_def = float(nguong_cfg.get("fill_ratio_diff_min", nguong_cfg.get("chenh_lech_toi_thieu", 0.10)))

    if not tat_ca_fill_ratios or len(tat_ca_fill_ratios) < 20:
        return {
            "fill_ratio_min": t_min_def,
            "fill_ratio_ambiguous": t_amb_def,
            "fill_ratio_diff_min": diff_min_def,
            "da_hieu_chinh": False,
        }

    arr = np.array(tat_ca_fill_ratios, dtype=np.float32)
    sorted_r = np.sort(arr)
    n = len(sorted_r)

    # Cụm 70% nhỏ nhất chắc chắn là các ô trống
    empty_cluster = sorted_r[:int(n * 0.70)]
    # Cụm 25% lớn nhất là các ứng viên ô đã được tô
    filled_candidates = sorted_r[int(n * 0.75):]

    empty_p90 = float(np.percentile(empty_cluster, 90))
    filled_p75 = float(np.percentile(filled_candidates, 75))

    gap = filled_p75 - empty_p90

    # Nếu có khoảng cách rõ ràng giữa cụm trống và cụm tô (học sinh có tô bài)
    if gap >= 0.14:
        t_min = float(np.clip(empty_p90 + 0.35 * gap, 0.26, 0.42))
        t_amb = float(np.clip(empty_p90 + 0.12 * gap, 0.15, 0.26))
        diff_min = float(np.clip(0.30 * gap, 0.06, 0.10))
        return {
            "fill_ratio_min": round(t_min, 4),
            "fill_ratio_ambiguous": round(t_amb, 4),
            "fill_ratio_diff_min": round(diff_min, 4),
            "da_hieu_chinh": True,
        }

    # Trường hợp phiếu để trống gần hết hoặc nét vẽ không rõ -> dùng ngưỡng mặc định an toàn
    return {
        "fill_ratio_min": t_min_def,
        "fill_ratio_ambiguous": t_amb_def,
        "fill_ratio_diff_min": diff_min_def,
        "da_hieu_chinh": False,
    }


def quyet_dinh_dap_an_cau(
    fill_ratios: dict[str, float],
    config: dict | None = None,
    nguong_tuy_chinh: dict | None = None
) -> tuple[str, str, float]:
    """
    Quyết định đáp án của 1 câu hỏi từ tỉ lệ tô fill_ratio của 4 lựa chọn (A, B, C, D).
    Hỗ trợ nhận diện chuẩn xác các đáp án tô mờ (nét chì nhạt / chưa kín ô):
    Nếu ô có mực/chì đen vượt trội hơn hẳn các ô trống còn lại thì tính là đáp án hợp lệ.

    Args:
        fill_ratios: Dict chứa tỉ lệ tô của từng lựa chọn, ví dụ {'A': 0.05, 'B': 0.85, 'C': 0.04, 'D': 0.02}.
        config: Dict cấu hình hệ thống (nếu None sẽ tự nạp từ config/config.json).
        nguong_tuy_chinh: Dict ngưỡng đã tự hiệu chỉnh theo phiếu (nếu có).

    Returns:
        tuple[str, str, float]:
            - lua_chon: 'A', 'B', 'C', 'D', 'BLANK', 'MULTI', hoặc 'AMBIGUOUS'
            - trang_thai: TRANG_THAI_HOP_LE, TRANG_THAI_BLANK, TRANG_THAI_MULTI, hoặc TRANG_THAI_AMBIGUOUS
            - max_fill_ratio: Tỉ lệ tô cao nhất trong 4 ô
    """
    if nguong_tuy_chinh:
        t_min = float(nguong_tuy_chinh["fill_ratio_min"])
        t_amb = float(nguong_tuy_chinh["fill_ratio_ambiguous"])
        diff_min = float(nguong_tuy_chinh["fill_ratio_diff_min"])
    else:
        if config is None:
            config = nap_config()
        nguong_cfg = config.get("nguong", {})
        t_min = float(nguong_cfg.get("fill_ratio_min", nguong_cfg.get("ti_le_to_min", 0.38)))
        t_amb = float(nguong_cfg.get("fill_ratio_ambiguous", nguong_cfg.get("ti_le_to_ambiguous", 0.24)))
        diff_min = float(nguong_cfg.get("fill_ratio_diff_min", nguong_cfg.get("chenh_lech_toi_thieu", 0.10)))

    # Sắp xếp các lựa chọn theo tỉ lệ giảm dần
    sorted_items = sorted(fill_ratios.items(), key=lambda x: x[1], reverse=True)
    best_opt, best_val = sorted_items[0]
    second_opt, second_val = sorted_items[1]
    gap = best_val - second_val

    # 1. Trường hợp MULTI: Có từ 2 ô trở lên cùng được tô đậm và chênh lệch rất nhỏ
    so_o_vuot_min = sum(1 for _, v in sorted_items if v >= max(t_min, 0.45))
    if so_o_vuot_min >= 2 and gap < 0.12:
        return TRANG_THAI_MULTI, TRANG_THAI_MULTI, best_val
    if best_val >= 0.40 and second_val >= 0.40 and gap < 0.10:
        return TRANG_THAI_MULTI, TRANG_THAI_MULTI, best_val

    # 2. Trường hợp BLANK: Không có ô nào vượt qua mức viền tròn in sẵn
    if best_val < 0.22 and gap < 0.08:
        return TRANG_THAI_BLANK, TRANG_THAI_BLANK, best_val
    if best_val < t_amb and gap < diff_min:
        return TRANG_THAI_BLANK, TRANG_THAI_BLANK, best_val

    # 3. Trường hợp HỢP LỆ (bao gồm cả nét tô đậm và nét tô mờ/nhạt):
    # Ô cao nhất vượt trội hơn hẳn ô thứ hai và đạt ngưỡng nhận diện nét chì
    if (best_val >= t_min and gap >= diff_min) or \
       (best_val >= 0.25 and gap >= 0.10) or \
       (best_val >= 0.30 and gap >= 0.08) or \
       (best_val >= 0.22 and gap >= 0.12):
        return best_opt, TRANG_THAI_HOP_LE, best_val

    # 4. Trường hợp thực sự nghi ngờ (2 ô cạnh tranh sát sao, ví dụ tẩy chưa sạch hoặc phân vân giữa 2 đáp án)
    if gap < 0.08 and second_val >= 0.25:
        return TRANG_THAI_AMBIGUOUS, TRANG_THAI_AMBIGUOUS, best_val

    # Nếu vẫn còn 1 ô cao hơn rõ ràng
    if gap >= 0.07 and best_val >= 0.22:
        return best_opt, TRANG_THAI_HOP_LE, best_val

    # Mặc định an toàn rơi vào AMBIGUOUS
    return TRANG_THAI_AMBIGUOUS, TRANG_THAI_AMBIGUOUS, best_val


def danh_gia_danh_sach_50(
    ket_qua_quet_50: list[dict[str, Any]],
    config: dict | None = None,
    tu_hieu_chinh: bool = True
) -> list[dict[str, Any]]:
    """
    Áp dụng logic quyết định cho toàn bộ 50 câu hỏi, tự động hiệu chỉnh ngưỡng theo phân bố nếu tu_hieu_chinh=True.

    Args:
        ket_qua_quet_50: Danh sách 50 dict chứa 'cau', 'fill_ratios', 'toa_do_tam', 'ban_kinh'.
        config: Dict cấu hình hệ thống.
        tu_hieu_chinh: Có kích hoạt tự động tính toán ngưỡng theo phiếu hay không.

    Returns:
        Danh sách 50 dict đã được bổ sung:
            - 'lua_chon': 'A'..'D' / 'BLANK' / 'MULTI' / 'AMBIGUOUS'
            - 'trang_thai': 'HOP_LE' / 'BLANK' / 'MULTI' / 'AMBIGUOUS'
            - 'max_ratio': float
            - 'nguong_su_dung': dict ngưỡng đã dùng
    """
    if config is None:
        config = nap_config()

    nguong_su_dung = None
    if tu_hieu_chinh:
        tat_ca_ratios = [val for item in ket_qua_quet_50 for val in item["fill_ratios"].values()]
        nguong_su_dung = tu_hieu_chinh_nguong_phieu(tat_ca_ratios, config)

    ket_qua_cuoi: list[dict[str, Any]] = []
    for item in ket_qua_quet_50:
        cau_so = item["cau"]
        ratios = item["fill_ratios"]
        lua_chon, trang_thai, max_r = quyet_dinh_dap_an_cau(ratios, config, nguong_su_dung)

        ket_qua_item = dict(item)
        ket_qua_item["lua_chon"] = lua_chon
        ket_qua_item["trang_thai"] = trang_thai
        ket_qua_item["max_ratio"] = max_r
        ket_qua_item["nguong_su_dung"] = nguong_su_dung
        ket_qua_cuoi.append(ket_qua_item)

    return ket_qua_cuoi

