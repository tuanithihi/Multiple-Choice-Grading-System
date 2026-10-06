"""
detect_sheet.py – Phát hiện biên và định vị 4 góc phiếu trả lời trong ảnh.

Cung cấp 2 chiến lược tìm phiếu:
    (a) Ưu tiên: Tìm 4 ô đánh dấu góc (marker vuông đen) có trên mẫu phiếu THPT.
    (b) Dự phòng: Tìm contour lớn nhất xấp xỉ thành tứ giác (approxPolyDP) khi chụp trên bàn.
Sắp xếp 4 đỉnh theo thứ tự chuẩn: Trên-Trái, Trên-Phải, Dưới-Phải, Dưới-Trái.
Ném lỗi có thông điệp tiếng Việt nếu không tìm thấy phiếu hợp lệ.
"""

import os
import cv2
import numpy as np

from omr.preprocess import (
    chuyen_grayscale,
    lam_mo_gaussian,
    phat_hien_canh_canny,
    dong_anh,
    luu_anh_debug,
    kiem_tra_chat_luong_anh,
    loai_bo_bong_do_va_can_bang_sang,
)


class LoiOMR(Exception):
    """Lớp ngoại lệ cơ sở cho hệ thống OMR."""
    pass


class LoiKhongTimThayPhieu(LoiOMR):
    """Ngoại lệ khi không thể phát hiện phiếu trả lời hợp lệ trong ảnh."""
    pass


def sap_xep_4_dinh(pts: np.ndarray) -> np.ndarray:
    """
    Sắp xếp 4 điểm góc của một tứ giác theo thứ tự cố định:
        1. Trên-Trái (Top-Left)
        2. Trên-Phải (Top-Right)
        3. Dưới-Phải (Bottom-Right)
        4. Dưới-Trái (Bottom-Left)

    Nguyên lý:
        - Điểm trên-trái có tổng x + y nhỏ nhất.
        - Điểm dưới-phải có tổng x + y lớn nhất.
        - Điểm trên-phải có hiệu x - y lớn nhất.
        - Điểm dưới-trái có hiệu x - y nhỏ nhất.

    Args:
        pts: Mảng numpy shape (4, 2) hoặc (4, 1, 2).

    Returns:
        np.ndarray shape (4, 2) kiểu float32 theo đúng thứ tự quy định.
    """
    pts = pts.reshape(4, 2).astype(np.float32)
    sap_xep = np.zeros((4, 2), dtype=np.float32)

    tong = pts.sum(axis=1)
    sap_xep[0] = pts[np.argmin(tong)]  # Trên-Trái
    sap_xep[2] = pts[np.argmax(tong)]  # Dưới-Phải

    hieu = pts[:, 0] - pts[:, 1]
    sap_xep[1] = pts[np.argmax(hieu)]  # Trên-Phải
    sap_xep[3] = pts[np.argmin(hieu)]  # Dưới-Trái

    return sap_xep


def _trich_xuat_candidates_marker(
    thresh: np.ndarray,
    H: int,
    W: int
) -> list[tuple[float, float, int, int, int, int]]:
    """
    Trích xuất danh sách các khối đen đặc vuông tiềm năng làm marker.
    Dùng cv2.RETR_LIST để không bị mất marker khi viền nền bàn tối bao quanh phiếu.
    """
    cnts, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    min_dim = max(10, int(min(H, W) * 0.012))
    max_dim = int(min(H, W) * 0.08)

    candidates: list[tuple[float, float, int, int, int, int]] = []
    for c in cnts:
        bx, by, bw, bh = cv2.boundingRect(c)
        if min_dim <= bw <= max_dim and min_dim <= bh <= max_dim:
            ar = bw / float(bh)
            if 0.65 <= ar <= 1.55:
                area = cv2.contourArea(c)
                extent = area / float(bw * bh)
                if extent >= 0.68:
                    cx = bx + bw / 2.0
                    cy = by + bh / 2.0
                    candidates.append((cx, cy, bx, by, bw, bh))
    return candidates


def _kiem_tra_va_lay_4_goc_marker(
    candidates: list[tuple[float, float, int, int, int, int]],
    H: int,
    W: int,
    min_area_ratio: float = 0.20
) -> np.ndarray | None:
    """Kiểm tra và trả về 4 góc đã sắp xếp nếu candidates tạo thành tứ giác marker hợp lệ."""
    if len(candidates) < 4:
        return None

    tl = min(candidates, key=lambda p: p[0] + p[1])
    br = max(candidates, key=lambda p: p[0] + p[1])
    tr = max(candidates, key=lambda p: p[0] - p[1])
    bl = min(candidates, key=lambda p: p[0] - p[1])

    # Kiểm tra 4 marker phải khác nhau
    tap_tam = {(round(p[0]), round(p[1])) for p in [tl, tr, br, bl]}
    if len(tap_tam) < 4:
        return None

    pts = np.float32([
        [tl[0], tl[1]],
        [tr[0], tr[1]],
        [br[0], br[1]],
        [bl[0], bl[1]]
    ])

    pts_int = pts.astype(np.int32)
    if not cv2.isContourConvex(pts_int):
        return None

    area = cv2.contourArea(pts_int)
    if area < min_area_ratio * (H * W):
        return None

    # Kiểm tra tỉ lệ hình học A4 (chấp nhận góc chụp nghiêng 1.05..1.95)
    w_top = np.linalg.norm(pts[1] - pts[0])
    w_bot = np.linalg.norm(pts[2] - pts[3])
    h_left = np.linalg.norm(pts[3] - pts[0])
    h_right = np.linalg.norm(pts[2] - pts[1])
    mean_w = (w_top + w_bot) / 2.0
    mean_h = (h_left + h_right) / 2.0
    if mean_w < 50 or mean_h < 50:
        return None
    ar = max(mean_w, mean_h) / min(mean_w, mean_h)
    if not (1.05 <= ar <= 1.95):
        return None

    return sap_xep_4_dinh(pts)


def tim_4_marker_goc(
    anh_gray: np.ndarray,
    min_area_ratio: float = 0.20
) -> tuple[np.ndarray | None, str]:
    """
    Chiến lược (a) - Ưu tiên:
    Tìm 4 ô vuông đen lớn nằm tại 4 góc của phiếu trắc nghiệm.
    Áp dụng nhiều cấp độ phân ngưỡng (thích nghi cục bộ, Otsu, cân bằng sáng) để chống chịu
    bóng đổ mạnh, ảnh thiếu sáng hoặc chênh lệch độ tương phản.

    Args:
        anh_gray: Ảnh mức xám.
        min_area_ratio: Tỉ lệ diện tích tối thiểu của tứ giác tạo bởi 4 marker so với ảnh.

    Returns:
        tuple[np.ndarray | None, str]: (Mảng 4 điểm [TL, TR, BR, BL] hoặc None, mô tả phương pháp).
    """
    H, W = anh_gray.shape[:2]
    bs = int(min(H, W) * 0.04) | 1

    # 1. Thử phân ngưỡng thích nghi cục bộ adaptiveThreshold với các tham số C khác nhau (15, 10, 8)
    for c_val in [15, 10, 8]:
        thresh_adapt = cv2.adaptiveThreshold(
            anh_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, bs, c_val
        )
        candidates_adapt = _trich_xuat_candidates_marker(thresh_adapt, H, W)
        pts = _kiem_tra_va_lay_4_goc_marker(candidates_adapt, H, W, min_area_ratio)
        if pts is not None:
            return pts, "marker"

    # 2. Thử phân ngưỡng Otsu trực tiếp
    _, thresh_otsu = cv2.threshold(anh_gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    candidates_otsu = _trich_xuat_candidates_marker(thresh_otsu, H, W)
    pts = _kiem_tra_va_lay_4_goc_marker(candidates_otsu, H, W, min_area_ratio)
    if pts is not None:
        return pts, "marker"

    # 3. Thử trên ảnh đã khử bóng đổ và cân bằng sáng
    anh_can_bang = loai_bo_bong_do_va_can_bang_sang(anh_gray)
    _, thresh_cb = cv2.threshold(anh_can_bang, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    candidates_cb = _trich_xuat_candidates_marker(thresh_cb, H, W)
    pts = _kiem_tra_va_lay_4_goc_marker(candidates_cb, H, W, min_area_ratio)
    if pts is not None:
        return pts, "marker"

    return None, "Không tìm thấy đủ 4 marker góc hợp lệ"


def tim_contour_to_giay(
    anh_gray: np.ndarray,
    min_area_ratio: float = 0.15
) -> tuple[np.ndarray | None, str]:
    """
    Chiến lược (b) - Dự phòng:
    Tìm đường viền lớn nhất của cả tờ giấy trắng nổi bật trên nền bàn lộn xộn.

    Args:
        anh_gray: Ảnh mức xám.
        min_area_ratio: Tỉ lệ diện tích tối thiểu so với khung hình.

    Returns:
        tuple[np.ndarray | None, str]: (Mảng 4 điểm [TL, TR, BR, BL] hoặc None, mô tả).
    """
    H, W = anh_gray.shape[:2]
    dien_tich_anh = H * W

    # Làm mờ và Canny
    blurred = lam_mo_gaussian(anh_gray, (5, 5))
    edges = phat_hien_canh_canny(blurred, 40, 120)
    closed = dong_anh(edges, (5, 5), iterations=2)

    cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None, "Không tìm thấy contour nào"

    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

    for c in cnts[:10]:
        area = cv2.contourArea(c)
        if area < min_area_ratio * dien_tich_anh:
            continue

        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.025 * peri, True)

        if len(approx) == 4 and cv2.isContourConvex(approx):
            pts = approx.reshape(4, 2).astype(np.float32)
            pts_sorted = sap_xep_4_dinh(pts)

            # 1. Kiểm tra tỉ lệ cạnh của tứ giác (A4 tỉ lệ ~1.41, chấp nhận méo nghiêng 1.10 - 1.90)
            tl, tr, br, bl = pts_sorted
            w_top = np.linalg.norm(tr - tl)
            w_bot = np.linalg.norm(br - bl)
            h_left = np.linalg.norm(bl - tl)
            h_right = np.linalg.norm(br - tr)

            mean_w = (w_top + w_bot) / 2.0
            mean_h = (h_left + h_right) / 2.0
            if mean_w < 20 or mean_h < 20:
                continue

            ar = max(mean_w, mean_h) / min(mean_w, mean_h)
            if not (1.10 <= ar <= 1.90):
                continue

            # 2. Kiểm tra độ sáng bên trong tứ giác (phải là giấy sáng màu > 45, hỗ trợ cả ảnh chụp thiếu sáng)
            mask = np.zeros((H, W), dtype=np.uint8)
            cv2.drawContours(mask, [pts_sorted.astype(np.int32)], -1, 255, -1)
            mean_val = cv2.mean(anh_gray, mask=mask)[0]
            if mean_val < 45:
                continue

            return pts_sorted, "contour"

    return None, "Không tìm thấy contour tứ giác hợp lệ"


def phat_hien_phieu(
    anh: np.ndarray,
    debug: bool = False,
    ten_debug: str = "phieu",
    thu_muc_debug: str = "outputs/debug"
) -> tuple[np.ndarray, str]:
    """
    Hàm phát hiện phiếu hoàn chỉnh kết hợp cả 2 chiến lược:
        1. Kiểm tra chất lượng ảnh đầu vào (quá tối, quá mờ, độ phân giải).
        2. Thử chiến lược (a) tìm 4 marker góc.
        3. Nếu thất bại, thử chiến lược (b) tìm contour tờ giấy.
        4. Kiểm tra xem phiếu có bị cắt mất góc / mất mép không.
        5. Ném ngoại lệ LoiKhongTimThayPhieu nếu không thể phát hiện.

    Args:
        anh: Ảnh numpy đầu vào (BGR hoặc Grayscale).
        debug: Có lưu ảnh debug các bước phát hiện không.
        ten_debug: Tiền tố tên file debug.
        thu_muc_debug: Thư mục chứa ảnh debug.

    Returns:
        tuple[np.ndarray, str]: (Mảng 4 đỉnh shape (4, 2) [TL, TR, BR, BL], phương pháp phát hiện).

    Raises:
        LoiKhongTimThayPhieu: Khi không tìm được phiếu trả lời trong ảnh.
    """
    # 0. Kiểm tra chất lượng ảnh đầu vào
    hop_le_chat_luong, ds_canh_bao = kiem_tra_chat_luong_anh(anh)
    if not hop_le_chat_luong:
        ly_do = "; ".join(ds_canh_bao)
        raise LoiKhongTimThayPhieu(f"❌ Ảnh đầu vào không hợp lệ ({ten_debug}): {ly_do}")

    anh_gray = chuyen_grayscale(anh)
    H, W = anh_gray.shape[:2]

    if debug:
        luu_anh_debug(anh_gray, f"{ten_debug}_1_grayscale.png", thu_muc_debug)
        edges = phat_hien_canh_canny(lam_mo_gaussian(anh_gray, (5, 5)), 50, 150)
        luu_anh_debug(edges, f"{ten_debug}_2_canny.png", thu_muc_debug)

    # 1. Thử tìm 4 marker góc (Chiến lược ưu tiên)
    pts_goc, phuong_phap = tim_4_marker_goc(anh_gray)

    # 2. Nếu không được, thử tìm contour tờ giấy (Chiến lược dự phòng)
    if pts_goc is None:
        pts_goc, phuong_phap = tim_contour_to_giay(anh_gray)

    # 3. Không tìm được phiếu hợp lệ -> Báo lỗi tiếng Việt chi tiết
    if pts_goc is None:
        canh_bao_str = f" Cảnh báo chất lượng: {', '.join(ds_canh_bao)}" if ds_canh_bao else ""
        raise LoiKhongTimThayPhieu(
            f"❌ Không tìm thấy phiếu trả lời hợp lệ trong ảnh ({ten_debug}). "
            f"Nguyên nhân có thể do ảnh quá tối, quá mờ, hoặc phiếu bị cắt mất góc / mất biên.{canh_bao_str} "
            f"Vui lòng đảm bảo chụp đủ 4 góc phiếu trong khung hình."
        )

    # Vẽ minh họa góc tìm được nếu bật debug
    if debug:
        vis = anh.copy() if len(anh.shape) == 3 else cv2.cvtColor(anh, cv2.COLOR_GRAY2BGR)
        pts_int = pts_goc.astype(np.int32)
        cv2.polylines(vis, [pts_int], isClosed=True, color=(0, 255, 0), thickness=3)

        ten_goc = ["TL (Tren-Trai)", "TR (Tren-Phai)", "BR (Duoi-Phai)", "BL (Duoi-Trai)"]
        mau_sac = [(255, 0, 0), (0, 165, 255), (0, 0, 255), (255, 0, 255)]
        for i, (pt, ten, mau) in enumerate(zip(pts_int, ten_goc, mau_sac)):
            cv2.circle(vis, tuple(pt), 10, mau, -1)
            cv2.putText(vis, ten, (pt[0] + 10, pt[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, mau, 2)

        luu_anh_debug(vis, f"{ten_debug}_3_detected_corners.png", thu_muc_debug)

    return pts_goc, phuong_phap

