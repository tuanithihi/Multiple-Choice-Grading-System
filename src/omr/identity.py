"""
identity.py – Đọc các khối Số báo danh (SBD) và Mã đề thi từ ảnh phiếu nắn phẳng.

Chức năng:
    - Quét lưới ô tròn theo từng CỘT trong khối SBD và Mã đề từ config.json.
    - Với mỗi cột: tính fill_ratio cho từng hàng (tương ứng chữ số từ 0 đến 9).
    - Chọn hàng có fill_ratio cao nhất vượt ngưỡng.
    - Xử lý các trường hợp ngoại lệ:
        + Cột không tô -> trả "?" cho chữ số đó và phát cảnh báo.
        + Cột tô nhiều ô -> trả "?" cho chữ số đó và phát cảnh báo.
        + Cột tô mờ/sát ngưỡng -> trả "?" và cảnh báo nghi ngờ.
    - Hỗ trợ vẽ minh họa debug khoanh ô được chọn lên ảnh.
"""

from typing import Any
import cv2
import numpy as np

from omr.config import nap_config
from omr.grade_logic import (
    TRANG_THAI_HOP_LE,
    TRANG_THAI_BLANK,
    TRANG_THAI_MULTI,
    TRANG_THAI_AMBIGUOUS,
)
from omr.preprocess import (
    chuyen_grayscale,
    nhi_phan_hoa,
    luu_anh_debug,
    loai_bo_bong_do_va_can_bang_sang,
    khu_nhieu,
)


def doc_khoi_chu_so(
    thresh: np.ndarray,
    roi_cfg: dict,
    nguong_cfg: dict,
    ten_khoi: str = "Khối"
) -> tuple[str, list[dict[str, Any]], list[str]]:
    """
    Đọc một khối chữ số (SBD hoặc Mã đề) theo từng cột từ trên xuống dưới (hàng 0-9).

    Args:
        thresh: Ảnh nhị phân Otsu đảo của phiếu đã nắn (255 là mực/chì, 0 là giấy).
        roi_cfg: Dict cấu hình của khối (pixel_x, pixel_y, so_cot, cot_x_offsets, hang_y_offsets, ban_kinh_o_pixel).
        nguong_cfg: Dict cấu hình ngưỡng (fill_ratio_min, fill_ratio_ambiguous, fill_ratio_diff_min).
        ten_khoi: Tên mô tả của khối dùng cho thông báo lỗi/cảnh báo (vd: "SBD", "Mã đề").

    Returns:
        tuple[str, list[dict], list[str]]:
            - chuoi_so: Chuỗi các chữ số đọc được, ví dụ "1234" hoặc "5?7".
            - chi_tiet_cot: Danh sách thông tin chi tiết từng cột.
            - danh_sach_canh_bao: Danh sách các cảnh báo (cột trống, tô nhiều ô, mờ).
    """
    t_min = float(nguong_cfg.get("fill_ratio_min", 0.38))
    t_amb = float(nguong_cfg.get("fill_ratio_ambiguous", 0.24))
    diff_min = float(nguong_cfg.get("fill_ratio_diff_min", 0.10))

    kx = roi_cfg["pixel_x"]
    ky = roi_cfg["pixel_y"]
    so_cot = int(roi_cfg.get("so_cot", 4))
    so_hang = int(roi_cfg.get("so_hang", 10))
    ban_kinh = int(roi_cfg.get("ban_kinh_o_pixel", 7))
    x_offsets = [float(x) for x in roi_cfg["cot_x_offsets"]]
    y_offsets = [float(y) for y in roi_cfg["hang_y_offsets"]]

    H, W = thresh.shape[:2]

    # Tạo mặt nạ hình tròn
    duong_kinh = 2 * ban_kinh + 1
    mat_na = np.zeros((duong_kinh, duong_kinh), dtype=np.uint8)
    cv2.circle(mat_na, (ban_kinh, ban_kinh), ban_kinh, 255, -1)
    tong_pixel_mat_na = float(np.count_nonzero(mat_na))

    chuoi_so = ""
    chi_tiet_cot: list[dict[str, Any]] = []
    danh_sach_canh_bao: list[str] = []

    for c_idx in range(so_cot):
        cx = int(round(kx + x_offsets[c_idx]))
        ratios: list[float] = []
        toa_do_tam: list[tuple[int, int]] = []

        for r_idx in range(so_hang):
            cy = int(round(ky + y_offsets[r_idx]))
            toa_do_tam.append((cx, cy))

            y1 = cy - ban_kinh
            y2 = cy + ban_kinh + 1
            x1 = cx - ban_kinh
            x2 = cx + ban_kinh + 1

            if y1 >= 0 and y2 <= H and x1 >= 0 and x2 <= W:
                patch = thresh[y1:y2, x1:x2]
                vung_to = cv2.bitwise_and(patch, mat_na)
                ratio = np.count_nonzero(vung_to) / tong_pixel_mat_na
            else:
                ratio = 0.0

            ratios.append(round(float(ratio), 4))

        # Phân tích kết quả theo hàng trong cột
        sorted_rows = sorted(enumerate(ratios), key=lambda x: x[1], reverse=True)
        best_row, best_val = sorted_rows[0]
        second_row, second_val = sorted_rows[1]

        rows_vuot_min = [r for r, val in sorted_rows if val >= t_min]

        # 1. Trường hợp MULTI: Có từ 2 ô trở lên vượt ngưỡng chuẩn
        if len(rows_vuot_min) >= 2:
            chu_so = "?"
            trang_thai = TRANG_THAI_MULTI
            hang_chon = None
            tam_chon = None
            msg = f"{ten_khoi}: Cột {c_idx + 1} tô nhiều ô ({', '.join(str(r) for r in sorted(rows_vuot_min))})"
            danh_sach_canh_bao.append(msg)

        # 2. Trường hợp BLANK: Không ô nào đạt ngưỡng tối thiểu
        elif best_val < t_amb:
            chu_so = "?"
            trang_thai = TRANG_THAI_BLANK
            hang_chon = None
            tam_chon = None
            msg = f"{ten_khoi}: Cột {c_idx + 1} không được tô"
            danh_sach_canh_bao.append(msg)

        # 3. Trường hợp AMBIGUOUS: Lưng chừng hoặc chênh lệch quá nhỏ
        elif (best_val < t_min) or ((best_val - second_val) < diff_min and second_val >= t_amb):
            chu_so = "?"
            trang_thai = TRANG_THAI_AMBIGUOUS
            hang_chon = best_row
            tam_chon = toa_do_tam[best_row]
            msg = f"{ten_khoi}: Cột {c_idx + 1} tô mờ/không rõ ràng (nghi ngờ số {best_row}, ratio={best_val:.2f})"
            danh_sach_canh_bao.append(msg)

        # 4. Trường hợp HỢP LỆ: 1 ô đạt chuẩn vượt trội
        else:
            chu_so = str(best_row)
            trang_thai = TRANG_THAI_HOP_LE
            hang_chon = best_row
            tam_chon = toa_do_tam[best_row]

        chuoi_so += chu_so
        chi_tiet_cot.append({
            "cot_idx": c_idx,
            "chu_so": chu_so,
            "trang_thai": trang_thai,
            "fill_ratios": ratios,
            "hang_chon": hang_chon,
            "tam_chon": tam_chon,
            "toa_do_tam": toa_do_tam,
            "ban_kinh": ban_kinh,
        })

    return chuoi_so, chi_tiet_cot, danh_sach_canh_bao


def ve_khoanh_identity(
    anh_phang: np.ndarray,
    ket_qua_identity: dict[str, Any],
    config: dict | None = None
) -> np.ndarray:
    """
    Vẽ trực quan hóa các ô đã chọn trong khối SBD và Mã đề.

    - Xanh lá: Ô hợp lệ được nhận diện.
    - Đỏ: Cột bị tô nhiều ô (MULTI).
    - Vàng: Ô sát ngưỡng nghi ngờ (AMBIGUOUS).
    """
    vis = anh_phang.copy()
    if len(vis.shape) == 2:
        vis = cv2.cvtColor(vis, cv2.COLOR_GRAY2BGR)

    if config is None:
        config = nap_config()

    nguong_cfg = config.get("nguong", {})
    t_min = float(nguong_cfg.get("fill_ratio_min", 0.38))

    for khoi_ten, chi_tiet in [("SBD", ket_qua_identity.get("chi_tiet_sbd", [])),
                              ("Mã đề", ket_qua_identity.get("chi_tiet_ma_de", []))]:
        for col_info in chi_tiet:
            st = col_info["trang_thai"]
            tam = col_info["tam_chon"]
            bk = col_info.get("ban_kinh", 7)
            toa_do_tam = col_info["toa_do_tam"]
            ratios = col_info["fill_ratios"]

            if st == TRANG_THAI_HOP_LE and tam is not None:
                cv2.circle(vis, tam, bk + 3, (0, 220, 0), 2)
            elif st == TRANG_THAI_MULTI:
                for r_idx, r_val in enumerate(ratios):
                    if r_val >= t_min:
                        cv2.circle(vis, toa_do_tam[r_idx], bk + 3, (0, 0, 255), 2)
            elif st == TRANG_THAI_AMBIGUOUS and tam is not None:
                cv2.circle(vis, tam, bk + 3, (0, 215, 255), 2)

    # Ghi text chuỗi SBD và Mã đề bên trên khối
    sbd_str = ket_qua_identity.get("sbd", "????")
    made_str = ket_qua_identity.get("ma_de", "???")

    sbd_cfg = config.get("roi_sbd", {})
    sx, sy = sbd_cfg.get("pixel_x", 747), sbd_cfg.get("pixel_y", 164)
    cv2.putText(vis, f"SBD: {sbd_str}", (sx, sy - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 140, 255), 2)

    made_cfg = config.get("roi_ma_de", {})
    mx, my = made_cfg.get("pixel_x", 895), made_cfg.get("pixel_y", 164)
    cv2.putText(vis, f"MD: {made_str}", (mx, my - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 0, 200), 2)

    return vis


def doc_sbd_va_ma_de(
    anh_phang: np.ndarray,
    config: dict | None = None,
    debug: bool = False,
    ten_debug: str = "identity",
    thu_muc_debug: str = "outputs/debug",
    nguong_tuy_chinh: dict | None = None
) -> dict[str, Any]:
    """
    Quy trình đọc hoàn chỉnh Số báo danh (SBD) và Mã đề thi từ ảnh phẳng.
    Tự động khử bóng đổ và cân bằng sáng trước khi nhị phân hóa.

    Args:
        anh_phang: Ảnh phiếu kích thước chuẩn (1055 x 1491 px).
        config: Dict cấu hình hệ thống.
        debug: Có lưu ảnh debug trực quan không.
        ten_debug: Tiền tố tên file debug.
        thu_muc_debug: Thư mục lưu ảnh debug.
        nguong_tuy_chinh: Ngưỡng tự hiệu chỉnh từ phân bố của phiếu (nếu có).

    Returns:
        Dict:
            - 'sbd': Chuỗi SBD (vd: "1234")
            - 'ma_de': Chuỗi Mã đề (vd: "567")
            - 'chi_tiet_sbd': list chi tiết từng cột SBD
            - 'chi_tiet_ma_de': list chi tiết từng cột Mã đề
            - 'warnings': list tổng hợp các cảnh báo
    """
    if config is None:
        config = nap_config()

    gray = chuyen_grayscale(anh_phang)
    # Khử nhiễu muối tiêu / mờ nhẹ và nén JPEG
    gray_denoise = khu_nhieu(gray)

    # Phân ngưỡng thích nghi cục bộ loại bỏ bóng đổ và chênh lệch sáng tối
    thresh = cv2.adaptiveThreshold(
        gray_denoise, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 41, 15
    )

    nguong_cfg = nguong_tuy_chinh if nguong_tuy_chinh else config.get("nguong", {})

    # 1. Đọc khối SBD
    sbd_str, chi_tiet_sbd, warnings_sbd = doc_khoi_chu_so(
        thresh, config["roi_sbd"], nguong_cfg, ten_khoi="SBD"
    )

    # 2. Đọc khối Mã đề
    made_str, chi_tiet_made, warnings_made = doc_khoi_chu_so(
        thresh, config["roi_ma_de"], nguong_cfg, ten_khoi="Mã đề"
    )

    ket_qua = {
        "sbd": sbd_str,
        "ma_de": made_str,
        "chi_tiet_sbd": chi_tiet_sbd,
        "chi_tiet_ma_de": chi_tiet_made,
        "warnings": warnings_sbd + warnings_made,
    }

    # 3. Xuất ảnh trực quan nếu bật debug
    if debug:
        vis = ve_khoanh_identity(anh_phang, ket_qua, config)
        luu_anh_debug(vis, f"identity_preview_{ten_debug}.png", thu_muc_debug)

    return ket_qua
