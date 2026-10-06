"""
warp.py – Cắt và nắn phối cảnh (perspective transform) cho phiếu trắc nghiệm.

Chức năng:
    - Nhận 4 điểm góc từ detect_sheet.py.
    - Áp dụng ma trận biến đổi phối cảnh (cv2.getPerspectiveTransform + cv2.warpPerspective)
      để tạo ảnh phẳng, đúng kích thước chuẩn (mặc định: 1055 x 1491 px).
    - Tự động phát hiện phiếu chụp xoay 90° hoặc ngược 180° và xoay lại đúng chiều.
    - Hỗ trợ lưu ảnh đã nắn và ảnh kiểm tra khớp ROI ra outputs/debug/.
"""

import os
import cv2
import numpy as np

from omr.config import nap_config
from omr.detect_sheet import phat_hien_phieu
from omr.preprocess import chuyen_grayscale, luu_anh_debug


# Tọa độ tâm 4 marker góc chuẩn trên ảnh kích thước 1055 × 1491 px (từ phiếu mẫu chuẩn)
TAM_MARKER_CHUAN = np.float32([
    [72.0, 76.5],     # Trên-Trái (TL)
    [985.0, 76.5],    # Trên-Phải (TR)
    [985.0, 1417.0],  # Dưới-Phải (BR)
    [72.5, 1417.0]    # Dưới-Trái (BL)
])


def kiem_tra_nguoc_180(anh_chuan: np.ndarray) -> bool:
    """
    Kiểm tra xem phiếu có bị chụp lộn ngược 180° hay không.

    Đặc trưng nhận diện chuẩn xác:
    - Ở nửa trên phiếu (y < 0.45 * H), cột ngăn cách x ~ 725 px (0.66..0.74 * W) có các marker vuông đen.
    - Nếu phiếu bị xoay ngược 180°, cột marker này sẽ chuyển sang góc dưới bên trái (x ~ 0.26..0.34 * W, y > 0.55 * H).
    - Đồng thời, ở giữa 2 cột câu hỏi (x: 0.46*W .. 0.54*W), có 6 cặp timing marks ở nửa dưới (y > 0.55*H) và không có ở nửa trên.

    Returns:
        True nếu phiếu đang bị lộn ngược 180°, False nếu đúng chiều xuôi.
    """
    gray = chuyen_grayscale(anh_chuan)
    H, W = gray.shape[:2]

    # Khử nhiễu và phân ngưỡng cục bộ để thích ứng với mọi điều kiện chiếu sáng / bóng đổ
    denoised = cv2.bilateralFilter(gray, d=5, sigmaColor=35, sigmaSpace=35)
    thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 41, 15)
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    marker_upright = 0
    marker_inverted = 0

    for c in cnts:
        bx, by, bw, bh = cv2.boundingRect(c)
        if 15 <= bw <= 45 and 15 <= bh <= 45 and 0.65 <= bw / float(bh) <= 1.5:
            extent = cv2.contourArea(c) / float(bw * bh)
            if extent >= 0.70:
                # Chiều xuôi: Marker ở cột x ~ 725 (0.66W..0.74W) nửa trên
                if int(0.66 * W) <= bx <= int(0.74 * W) and by < H * 0.45:
                    marker_upright += 1
                # Chiều ngược 180: Cột marker bị lộn xuống x ~ 330 (0.26W..0.34W) nửa dưới
                elif int(0.26 * W) <= bx <= int(0.34 * W) and by > H * 0.55:
                    marker_inverted += 1

    if marker_inverted > marker_upright:
        return True
    if marker_upright > marker_inverted:
        return False

    # Kiểm tra phụ trợ bằng mật độ timing marks giữa 2 cột (x: 0.46*W .. 0.54*W) trên ảnh nhị phân
    timing_top = np.count_nonzero(thresh[int(0.05 * H):int(0.40 * H), int(0.46 * W):int(0.54 * W)])
    timing_bot = np.count_nonzero(thresh[int(0.60 * H):int(0.95 * H), int(0.46 * W):int(0.54 * W)])
    if timing_top > timing_bot * 2.5 and marker_upright == 0:
        return True

    return False


def chuan_hoa_chieu_phieu(anh: np.ndarray) -> np.ndarray:
    """
    Tự động chuẩn hóa chiều quay của phiếu:
        - Nếu ảnh nằm ngang (width > height): xoay 90° theo chiều kim đồng hồ.
        - Nếu ảnh bị ngược 180°: xoay 180° về chiều xuôi chuẩn.

    Args:
        anh: Ảnh sau khi cắt/nắn.

    Returns:
        np.ndarray: Ảnh phiếu thẳng, đứng và đúng chiều.
    """
    ket_qua = anh.copy()
    h, w = ket_qua.shape[:2]

    # 1. Nếu ảnh nằm ngang -> Xoay 90° sang đứng
    if w > h:
        ket_qua = cv2.rotate(ket_qua, cv2.ROTATE_90_CLOCKWISE)

    # 2. Kiểm tra có bị ngược 180° không
    if kiem_tra_nguoc_180(ket_qua):
        ket_qua = cv2.rotate(ket_qua, cv2.ROTATE_180)

    return ket_qua


def nan_phoi_canh(
    anh: np.ndarray,
    pts_4_goc: np.ndarray,
    che_do: str = "marker",
    chieu_rong: int = 1055,
    chieu_cao: int = 1491
) -> np.ndarray:
    """
    Thực hiện biến đổi phối cảnh (warpPerspective) đưa phiếu về ảnh chuẩn kích thước.

    Args:
        anh: Ảnh numpy gốc.
        pts_4_goc: Mảng 4 điểm [TL, TR, BR, BL] (shape 4, 2).
        che_do: 'marker' (nắn theo 4 tâm marker) hoặc 'contour' (nắn theo 4 góc viền giấy).
        chieu_rong: Chiều rộng ảnh chuẩn (mặc định 1055 px).
        chieu_cao: Chiều cao ảnh chuẩn (mặc định 1491 px).

    Returns:
        np.ndarray: Ảnh đã nắn thẳng, đúng kích thước và đúng chiều.
    """
    src_pts = pts_4_goc.astype(np.float32)

    if che_do == "marker":
        # Ánh xạ 4 marker về đúng tọa độ marker trên ảnh chuẩn
        # Điều chỉnh tỉ lệ nếu chieu_rong, chieu_cao khác 1055x1491
        scale_x = chieu_rong / 1055.0
        scale_y = chieu_cao / 1491.0
        dst_pts = TAM_MARKER_CHUAN.copy()
        dst_pts[:, 0] *= scale_x
        dst_pts[:, 1] *= scale_y
    else:
        # Nắn 4 góc tờ giấy về 4 góc khung hình (0,0) -> (W, H)
        dst_pts = np.float32([
            [0.0, 0.0],
            [float(chieu_rong), 0.0],
            [float(chieu_rong), float(chieu_cao)],
            [0.0, float(chieu_cao)]
        ])

    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped = cv2.warpPerspective(
        anh, M, (chieu_rong, chieu_cao),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255)
    )

    # Chuẩn hóa chiều xuôi
    warped_dung_chieu = chuan_hoa_chieu_phieu(warped)
    return warped_dung_chieu


def ve_kiem_tra_roi(anh_warped: np.ndarray, config: dict) -> np.ndarray:
    """
    Vẽ các ROI (SBD, Mã đề, 10 khối câu hỏi, Marker) lên ảnh đã nắn
    để kiểm tra trực quan độ trùng khớp chính xác.
    """
    vis = anh_warped.copy()
    if len(vis.shape) == 2:
        vis = cv2.cvtColor(vis, cv2.COLOR_GRAY2BGR)

    # 1. Vẽ 4 Marker góc (Xanh dương)
    for k, m in config.get("markers_goc", {}).items():
        if k.startswith("_"):
            continue
        x, y, w, h = m["x"], m["y"], m["w"], m["h"]
        cv2.rectangle(vis, (x, y), (x + w, y + h), (255, 0, 0), 2)

    # 2. Vẽ ROI SBD (Cam)
    sbd = config.get("roi_sbd", {})
    sx, sy = sbd.get("pixel_x", 0), sbd.get("pixel_y", 0)
    sw, sh = sbd.get("pixel_w", 0), sbd.get("pixel_h", 0)
    cv2.rectangle(vis, (sx, sy), (sx + sw, sy + sh), (0, 140, 255), 2)
    cv2.putText(vis, f"SBD ({sbd.get('so_cot')} cot)", (sx, sy - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 140, 255), 2)

    # 3. Vẽ ROI Mã đề (Tím)
    made = config.get("roi_ma_de", {})
    mx, my = made.get("pixel_x", 0), made.get("pixel_y", 0)
    mw, mh = made.get("pixel_w", 0), made.get("pixel_h", 0)
    cv2.rectangle(vis, (mx, my), (mx + mw, my + mh), (200, 0, 200), 2)
    cv2.putText(vis, f"Ma de ({made.get('so_cot')} cot)", (mx, my - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 0, 200), 2)

    # 4. Vẽ 10 khối câu hỏi (Xanh lá)
    for khoi in config.get("roi_cau_hoi", {}).get("khoi", []):
        kx, ky = khoi.get("pixel_x", 0), khoi.get("pixel_y", 0)
        kw, kh = khoi.get("pixel_w", 0), khoi.get("pixel_h", 0)
        cv2.rectangle(vis, (kx, ky), (kx + kw, ky + kh), (0, 200, 0), 2)
        ten = khoi.get("ten", "")
        cv2.putText(vis, ten, (kx + 5, ky + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 120, 0), 2)

    return vis


def xu_ly_va_nan_phieu(
    anh: np.ndarray,
    config: dict | None = None,
    debug: bool = False,
    ten_debug: str = "phieu",
    thu_muc_debug: str = "outputs/debug"
) -> tuple[np.ndarray, np.ndarray, str]:
    """
    Quy trình tích hợp hoàn chỉnh của Giai đoạn 3:
        1. Nạp config (nếu chưa truyền vào).
        2. Tìm 4 góc phiếu (detect_sheet.py).
        3. Nắn phối cảnh về kích thước chuẩn config.
        4. Tự sửa chiều quay (xoay 90° hoặc 180° nếu bị ngược).
        5. Nếu debug: lưu ảnh đã nắn và ảnh vẽ đè ROI kiểm tra khớp.

    Args:
        anh: Ảnh numpy đầu vào.
        config: Dict cấu hình (nếu None sẽ tự nạp từ config/config.json).
        debug: Có bật chế độ debug không.
        ten_debug: Tên nhận diện file debug.
        thu_muc_debug: Thư mục lưu ảnh debug.

    Returns:
        tuple[np.ndarray, np.ndarray, str]:
            - anh_warped: Ảnh phiếu đã nắn thẳng kích thước chuẩn (1055 x 1491).
            - pts_goc: 4 điểm góc phát hiện được trên ảnh gốc.
            - phuong_phap: 'marker' hoặc 'contour' hoặc 'toan_bo_khung_anh'.
    """
    if config is None:
        config = nap_config()

    chieu_rong = config["anh"]["chieu_rong"]
    chieu_cao = config["anh"]["chieu_cao"]

    # 1. Phát hiện 4 góc phiếu
    pts_goc, phuong_phap = phat_hien_phieu(
        anh, debug=debug, ten_debug=ten_debug, thu_muc_debug=thu_muc_debug
    )

    # 2. Nắn phối cảnh
    che_do = "marker" if phuong_phap == "marker" else "contour"
    anh_warped = nan_phoi_canh(
        anh, pts_goc, che_do=che_do, chieu_rong=chieu_rong, chieu_cao=chieu_cao
    )

    # 3. Ghi nhận ảnh debug nếu bật cờ
    if debug:
        luu_anh_debug(anh_warped, f"{ten_debug}_4_warped.png", thu_muc_debug)
        anh_roi = ve_kiem_tra_roi(anh_warped, config)
        luu_anh_debug(anh_roi, f"{ten_debug}_5_roi_verified.png", thu_muc_debug)

    return anh_warped, pts_goc, phuong_phap
