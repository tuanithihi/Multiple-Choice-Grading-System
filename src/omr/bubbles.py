"""
bubbles.py – Phát hiện và tính toán tỉ lệ tô các ô tròn (bubbles) trắc nghiệm.

Chức năng:
    - Nhị phân hóa ảnh phiếu đã nắn bằng Otsu đảo (mực/chì thành màu trắng 255 trên nền đen 0).
    - Cắt lưới ô tròn của từng khối câu hỏi theo tọa độ từ config.json (không hard-code).
    - Dùng mặt nạ hình tròn bên trong ô (bán kính cấu hình) để loại trừ viền tròn in sẵn.
    - Tính fill_ratio = (số pixel trắng trong mặt nạ) / (tổng số pixel trong mặt nạ).
    - Hỗ trợ vẽ minh họa kết quả đọc lên ảnh debug (xanh lá: hợp lệ, đỏ: MULTI, vàng: AMBIGUOUS).
"""

from typing import Any
import cv2
import numpy as np

from omr.config import nap_config
from omr.grade_logic import (
    danh_gia_danh_sach_50,
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


def tao_mat_na_tron(ban_kinh: int) -> tuple[np.ndarray, int]:
    """
    Tạo mặt nạ hình tròn nhị phân 2D kích thước (2R+1, 2R+1).

    Args:
        ban_kinh: Bán kính vùng tính toán (pixel).

    Returns:
        tuple[np.ndarray, int]: (Mặt nạ uint8 có giá trị 255 trong hình tròn và 0 bên ngoài,
                                 Tổng số pixel trong hình tròn).
    """
    duong_kinh = 2 * ban_kinh + 1
    mat_na = np.zeros((duong_kinh, duong_kinh), dtype=np.uint8)
    cv2.circle(mat_na, (ban_kinh, ban_kinh), ban_kinh, 255, -1)
    tong_pixel = int(np.count_nonzero(mat_na))
    return mat_na, tong_pixel


def quet_o_to(
    anh_phang: np.ndarray,
    config: dict | None = None
) -> list[dict[str, Any]]:
    """
    Quét và tính tỉ lệ tô fill_ratio cho toàn bộ 50 câu hỏi trên ảnh phiếu đã nắn phẳng.
    Tự động khử bóng đổ, cân bằng sáng và khử nhiễu trước khi nhị phân hóa.

    Args:
        anh_phang: Ảnh phiếu đã nắn phẳng kích thước chuẩn (1055 x 1491 px).
        config: Dict cấu hình hệ thống (nếu None sẽ tự nạp từ config/config.json).

    Returns:
        Danh sách 50 dict, mỗi dict chứa:
            - 'cau': số thứ tự câu (1 đến 50)
            - 'fill_ratios': dict {'A': float, 'B': float, 'C': float, 'D': float}
            - 'toa_do_tam': dict {'A': (cx, cy), ...}
            - 'ban_kinh': int
    """
    if config is None:
        config = nap_config()

    gray = chuyen_grayscale(anh_phang)
    # Khử nhiễu muối tiêu / mờ nhẹ và nén JPEG
    gray_denoise = khu_nhieu(gray)

    # Phân ngưỡng thích nghi cục bộ: nét chì/mực thành trắng (255), nền giấy thành đen (0)
    # Giúp xử lý hoàn hảo bóng đổ một phần phiếu hoặc chênh lệch sáng tối lớn
    thresh = cv2.adaptiveThreshold(
        gray_denoise, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 41, 15
    )

    roi_cfg = config["roi_cau_hoi"]
    ban_kinh = int(roi_cfg.get("ban_kinh_o_pixel", 8))
    y_offsets = [float(y) for y in roi_cfg.get("hang_y_offsets", [16.6, 47.4, 78.4, 109.3, 140.2])]
    x_offsets_col1 = [float(x) for x in roi_cfg.get("cot_1_5_x_offsets", [90.0, 155.5, 219.7, 283.6])]
    x_offsets_col2 = [float(x) for x in roi_cfg.get("cot_6_10_x_offsets", [88.5, 151.5, 220.0, 288.0])]
    nhan_dap_an = roi_cfg.get("dap_an_nhan", ["A", "B", "C", "D"])

    mat_na, tong_pixel_mat_na = tao_mat_na_tron(ban_kinh)
    H, W = thresh.shape[:2]

    danh_sach_cau: list[dict[str, Any]] = []

    for b_idx, khoi in enumerate(roi_cfg["khoi"]):
        kx = khoi["pixel_x"]
        ky = khoi["pixel_y"]
        tu_cau = khoi["tu_cau"]
        x_offsets = x_offsets_col1 if b_idx < 5 else x_offsets_col2

        for r_idx, y_off in enumerate(y_offsets):
            cau_so = tu_cau + r_idx
            cy = int(round(ky + y_off))

            fill_ratios: dict[str, float] = {}
            toa_do_tam: dict[str, tuple[int, int]] = {}

            for c_idx, x_off in enumerate(x_offsets):
                ch = nhan_dap_an[c_idx]
                cx = int(round(kx + x_off))

                # Trích xuất patch quanh tâm ô tròn lý thuyết
                y1 = cy - ban_kinh
                y2 = cy + ban_kinh + 1
                x1 = cx - ban_kinh
                x2 = cx + ban_kinh + 1

                if y1 >= 0 and y2 <= H and x1 >= 0 and x2 <= W:
                    patch0 = thresh[y1:y2, x1:x2]
                    vung_to0 = cv2.bitwise_and(patch0, mat_na)
                    ratio0 = int(np.count_nonzero(vung_to0)) / float(tong_pixel_mat_na)
                else:
                    ratio0 = 0.0

                # Tinh chỉnh vị trí tâm ô tròn trong khoảng dịch chuyển cục bộ [-10, 10] px
                # để chống lệch tọa độ do in ấn / quét / phối cảnh nhẹ, và bắt trọn nét tô mờ
                best_r = ratio0
                best_cx = cx
                best_cy = cy

                if ratio0 < 0.65:
                    for dx in (-10, -8, -6, -4, -2, 2, 4, 6, 8, 10):
                        for dy in (-10, -8, -6, -4, -2, 2, 4, 6, 8, 10):
                            ny1 = cy + dy - ban_kinh
                            ny2 = cy + dy + ban_kinh + 1
                            nx1 = cx + dx - ban_kinh
                            nx2 = cx + dx + ban_kinh + 1
                            if ny1 >= 0 and ny2 <= H and nx1 >= 0 and nx2 <= W:
                                p = thresh[ny1:ny2, nx1:nx2]
                                v = cv2.bitwise_and(p, mat_na)
                                r_curr = int(np.count_nonzero(v)) / float(tong_pixel_mat_na)
                                if r_curr > best_r:
                                    best_r = r_curr
                                    best_cx = cx + dx
                                    best_cy = cy + dy

                toa_do_tam[ch] = (best_cx, best_cy)
                fill_ratios[ch] = round(best_r, 4)

            danh_sach_cau.append({
                "cau": cau_so,
                "fill_ratios": fill_ratios,
                "toa_do_tam": toa_do_tam,
                "ban_kinh": ban_kinh,
            })

    return danh_sach_cau


def ve_ket_qua_cau_hoi(
    anh_phang: np.ndarray,
    danh_sach_50: list[dict[str, Any]],
    config: dict | None = None
) -> np.ndarray:
    """
    Vẽ minh họa kết quả đọc 50 câu hỏi lên ảnh phẳng:
        - Xanh lá (BGR: 0, 255, 0): Ô được nhận diện là đã tô hợp lệ.
        - Đỏ (BGR: 0, 0, 255): Câu tô nhiều ô (MULTI).
        - Vàng (BGR: 0, 215, 255): Câu nghi ngờ sát ngưỡng (AMBIGUOUS).
        - Ghi chú số câu và kết quả nhận diện ở lề trái mỗi khối câu.

    Args:
        anh_phang: Ảnh phẳng gốc.
        danh_sach_50: Danh sách 50 kết quả câu hỏi từ doc_50_cau_hoi.
        config: Dict cấu hình.

    Returns:
        np.ndarray: Ảnh BGR đã vẽ trực quan hóa kết quả đọc.
    """
    vis = anh_phang.copy()
    if len(vis.shape) == 2:
        vis = cv2.cvtColor(vis, cv2.COLOR_GRAY2BGR)

    for item in danh_sach_50:
        cau_so = item["cau"]
        lua_chon = item["lua_chon"]
        trang_thai = item["trang_thai"]
        toa_do = item["toa_do_tam"]
        ban_kinh = item["ban_kinh"]

        # Tọa độ điểm bắt đầu viết chữ (ở bên trái lựa chọn A)
        pt_a = toa_do["A"]
        text_x = pt_a[0] - 55
        text_y = pt_a[1] + 5

        if trang_thai == TRANG_THAI_HOP_LE:
            # Khoanh xanh lá ô đã tô
            tam = toa_do[lua_chon]
            cv2.circle(vis, tam, ban_kinh + 4, (0, 220, 0), 2)
            cv2.putText(vis, f"{cau_so:02d}:{lua_chon}", (text_x, text_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 150, 0), 1)

        elif trang_thai == TRANG_THAI_MULTI:
            # Khoanh đỏ các ô có tỉ lệ cao
            t_min = 0.38
            if config:
                t_min = float(config.get("nguong", {}).get("fill_ratio_min", 0.38))
            for opt, r in item["fill_ratios"].items():
                if r >= t_min:
                    cv2.circle(vis, toa_do[opt], ban_kinh + 4, (0, 0, 255), 2)
            cv2.putText(vis, f"{cau_so:02d}:MUL", (text_x, text_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 255), 1)

        elif trang_thai == TRANG_THAI_AMBIGUOUS:
            # Khoanh vàng ô nghi ngờ
            max_opt = max(item["fill_ratios"].items(), key=lambda x: x[1])[0]
            cv2.circle(vis, toa_do[max_opt], ban_kinh + 4, (0, 215, 255), 2)
            cv2.putText(vis, f"{cau_so:02d}:AMB", (text_x, text_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 180, 210), 1)

        else:  # BLANK
            cv2.putText(vis, f"{cau_so:02d}:--", (text_x, text_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (120, 120, 120), 1)

    return vis


def doc_50_cau_hoi(
    anh_phang: np.ndarray,
    config: dict | None = None,
    debug: bool = False,
    ten_debug: str = "cau_hoi",
    thu_muc_debug: str = "outputs/debug"
) -> list[dict[str, Any]]:
    """
    Quy trình trọn gói đọc 50 câu hỏi trắc nghiệm từ ảnh phiếu đã nắn phẳng.

    Args:
        anh_phang: Ảnh phiếu kích thước chuẩn (1055 x 1491 px).
        config: Dict cấu hình hệ thống.
        debug: Có lưu ảnh debug trực quan không.
        ten_debug: Tiền tố tên file debug.
        thu_muc_debug: Thư mục lưu ảnh debug.

    Returns:
        Danh sách 50 dict chứa đầy đủ thông tin:
            - 'cau': int (1..50)
            - 'lua_chon': 'A'..'D' / 'BLANK' / 'MULTI' / 'AMBIGUOUS'
            - 'trang_thai': 'HOP_LE' / 'BLANK' / 'MULTI' / 'AMBIGUOUS'
            - 'max_ratio': float
            - 'fill_ratios': dict {'A': float, 'B': float, 'C': float, 'D': float}
            - 'toa_do_tam': dict {'A': (x, y), ...}
            - 'ban_kinh': int
    """
    if config is None:
        config = nap_config()

    # 1. Quét tỉ lệ tô của 50 câu
    raw_results = quet_o_to(anh_phang, config)

    # 2. Đánh giá và quyết định đáp án từng câu
    danh_sach_cuoi = danh_gia_danh_sach_50(raw_results, config)

    # 3. Vẽ và lưu ảnh debug nếu bật cờ
    if debug:
        vis = ve_ket_qua_cau_hoi(anh_phang, danh_sach_cuoi, config)
        luu_anh_debug(vis, f"bubbles_preview_{ten_debug}.png", thu_muc_debug)

    return danh_sach_cuoi
