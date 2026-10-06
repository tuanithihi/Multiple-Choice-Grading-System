"""
preprocess.py – Tiền xử lý ảnh phiếu trả lời trắc nghiệm OMR.

Cung cấp các hàm xử lý ảnh cổ điển:
    - Thay đổi kích thước giữ nguyên tỉ lệ (resize)
    - Chuyển đổi không gian màu sang grayscale
    - Làm mờ giảm nhiễu (Gaussian Blur)
    - Nhị phân hóa (Otsu, Adaptive, Fixed threshold)
    - Phát hiện cạnh (Canny Edge Detection)
    - Phép toán hình thái học (Morphology: Dilation, Closing, Opening)
    - Lưu ảnh trung gian cho chế độ gỡ lỗi (--debug)
"""

import os
import cv2
import numpy as np


def thay_doi_kich_thuoc_giu_ti_le(
    anh: np.ndarray,
    chieu_dai_max: int = 1500
) -> tuple[np.ndarray, float]:
    """
    Thay đổi kích thước ảnh giữ nguyên tỉ lệ khung hình nếu kích thước vượt quá giới hạn.

    Args:
        anh: Ảnh numpy đầu vào.
        chieu_dai_max: Kích thước cạnh dài nhất tối đa cho phép.

    Returns:
        tuple[np.ndarray, float]: (ảnh sau khi resize, tỉ lệ co dãn tỉ lệ = mới / cũ).
    """
    h, w = anh.shape[:2]
    canh_lon = max(h, w)
    if canh_lon <= chieu_dai_max:
        return anh.copy(), 1.0

    ti_le = chieu_dai_max / float(canh_lon)
    w_moi = int(round(w * ti_le))
    h_moi = int(round(h * ti_le))
    anh_resized = cv2.resize(anh, (w_moi, h_moi), interpolation=cv2.INTER_AREA)
    return anh_resized, ti_le


def chuyen_grayscale(anh: np.ndarray) -> np.ndarray:
    """
    Chuyển ảnh BGR sang ảnh mức xám (grayscale).

    Args:
        anh: Ảnh numpy đầu vào (BGR hoặc grayscale).

    Returns:
        np.ndarray: Ảnh mức xám 1 kênh uint8.
    """
    if len(anh.shape) == 2:
        return anh.copy()
    return cv2.cvtColor(anh, cv2.COLOR_BGR2GRAY)


def lam_mo_gaussian(
    anh_gray: np.ndarray,
    ksize: tuple[int, int] = (5, 5),
    sigma_x: float = 0
) -> np.ndarray:
    """
    Làm mờ ảnh bằng Gaussian Filter để triệt tiêu nhiễu tần số cao.

    Args:
        anh_gray: Ảnh mức xám đầu vào.
        ksize: Kích thước kernel làm mờ (mặc định (5, 5)).
        sigma_x: Độ lệch chuẩn Gaussian (0 để OpenCV tự tính từ ksize).

    Returns:
        np.ndarray: Ảnh xám đã làm mờ.
    """
    return cv2.GaussianBlur(anh_gray, ksize, sigma_x)


def nhi_phan_hoa(
    anh_gray: np.ndarray,
    kieu: str = "otsu",
    dao_nguoc: bool = True,
    nguong_co_dinh: int = 127
) -> np.ndarray:
    """
    Nhị phân hóa ảnh mức xám.

    Args:
        anh_gray: Ảnh mức xám đầu vào.
        kieu: Thuật toán ngưỡng ('otsu', 'adaptive', 'fixed').
        dao_nguoc: Nếu True, vùng nét vẽ/mực đen thành màu trắng (255) trên nền đen (0)
                   (thuận lợi cho đếm pixel tô và tìm contour).
        nguong_co_dinh: Ngưỡng cố định nếu dùng kieu='fixed'.

    Returns:
        np.ndarray: Ảnh nhị phân (0 và 255).
    """
    flag = cv2.THRESH_BINARY_INV if dao_nguoc else cv2.THRESH_BINARY

    if kieu == "otsu":
        _, nhi_phan = cv2.threshold(anh_gray, 0, 255, flag | cv2.THRESH_OTSU)
    elif kieu == "adaptive":
        adaptive_flag = cv2.THRESH_BINARY_INV if dao_nguoc else cv2.THRESH_BINARY
        nhi_phan = cv2.adaptiveThreshold(
            anh_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            adaptive_flag, 15, 4
        )
    else:
        _, nhi_phan = cv2.threshold(anh_gray, nguong_co_dinh, 255, flag)

    return nhi_phan


def phat_hien_canh_canny(
    anh_gray: np.ndarray,
    low_thresh: int = 50,
    high_thresh: int = 150
) -> np.ndarray:
    """
    Phát hiện cạnh bằng giải thuật Canny Edge Detector.

    Args:
        anh_gray: Ảnh mức xám đầu vào.
        low_thresh: Ngưỡng dưới.
        high_thresh: Ngưỡng trên.

    Returns:
        np.ndarray: Ảnh cạnh (binary 0 và 255).
    """
    return cv2.Canny(anh_gray, low_thresh, high_thresh)


def gian_anh(
    anh_bin: np.ndarray,
    ksize: tuple[int, int] = (3, 3),
    iterations: int = 1
) -> np.ndarray:
    """
    Phép giãn hình ảnh (Dilation) để làm dày các nét cạnh và nối liền đứt gãy nhỏ.

    Args:
        anh_bin: Ảnh nhị phân hoặc cạnh.
        ksize: Kích thước phần tử cấu trúc (kernel).
        iterations: Số lần áp dụng.

    Returns:
        np.ndarray: Ảnh sau khi giãn.
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, ksize)
    return cv2.dilate(anh_bin, kernel, iterations=iterations)


def dong_anh(
    anh_bin: np.ndarray,
    ksize: tuple[int, int] = (5, 5),
    iterations: int = 1
) -> np.ndarray:
    """
    Phép đóng hình thái học (Morphological Closing = Dilation + Erosion)
    để nối liền các nét đứt trên viền phiếu trả lời.

    Args:
        anh_bin: Ảnh nhị phân hoặc cạnh.
        ksize: Kích thước phần tử cấu trúc.
        iterations: Số lần lặp.

    Returns:
        np.ndarray: Ảnh sau khi đóng nét.
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, ksize)
    return cv2.morphologyEx(anh_bin, cv2.MORPH_CLOSE, kernel, iterations=iterations)


def mo_anh(
    anh_bin: np.ndarray,
    ksize: tuple[int, int] = (3, 3),
    iterations: int = 1
) -> np.ndarray:
    """
    Phép mở hình thái học (Morphological Opening = Erosion + Dilation)
    để loại bỏ các đốm nhiễu li ti độc lập.

    Args:
        anh_bin: Ảnh nhị phân.
        ksize: Kích thước kernel.
        iterations: Số lần lặp.

    Returns:
        np.ndarray: Ảnh sau khi lọc nhiễu.
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, ksize)
    return cv2.morphologyEx(anh_bin, cv2.MORPH_OPEN, kernel, iterations=iterations)


def luu_anh_debug(
    anh: np.ndarray,
    ten_file: str,
    thu_muc_debug: str = "outputs/debug"
) -> str | None:
    """
    Lưu ảnh trung gian phục vụ kiểm tra và gỡ lỗi (hỗ trợ đường dẫn Unicode tiếng Việt).

    Args:
        anh: Ảnh numpy cần lưu.
        ten_file: Tên file đích (ví dụ 'debug_canny.png').
        thu_muc_debug: Thư mục chứa file debug.

    Returns:
        Đường dẫn file đã lưu hoặc None nếu thất bại.
    """
    try:
        os.makedirs(thu_muc_debug, exist_ok=True)
        duong_dan = os.path.join(thu_muc_debug, ten_file)
        ext = os.path.splitext(ten_file)[1]
        if not ext:
            ext = ".png"
            duong_dan += ext
        thanh_cong, buffer = cv2.imencode(ext, anh)
        if thanh_cong:
            with open(duong_dan, "wb") as f:
                f.write(buffer)
            return duong_dan
        return None
    except Exception:
        return None


def kiem_tra_chat_luong_anh(anh: np.ndarray | None) -> tuple[bool, list[str]]:
    """
    Kiểm tra chất lượng ảnh đầu vào: quá tối, quá sáng/lóa, quá mờ nét, kích thước quá nhỏ.

    Args:
        anh: Ảnh numpy đầu vào (BGR hoặc Grayscale).

    Returns:
        tuple[bool, list[str]]: (hop_le: bool, danh_sach_canh_bao: list[str])
    """
    if anh is None or not hasattr(anh, "size") or anh.size == 0:
        return False, ["Ảnh không có dữ liệu hoặc file bị hỏng."]

    h, w = anh.shape[:2]
    if h < 300 or w < 300:
        return False, [f"Độ phân giải ảnh quá nhỏ ({w}×{h} px), tối thiểu cần 300×300 px."]

    gray = chuyen_grayscale(anh)
    canh_bao: list[str] = []

    # 1. Kiểm tra độ sáng trung bình
    mean_val = float(np.mean(gray))
    if mean_val < 50.0:
        canh_bao.append(f"Ảnh quá tối (độ sáng trung bình: {mean_val:.1f}/255). Hãy bổ sung ánh sáng khi chụp.")
    elif mean_val > 235.0:
        canh_bao.append(f"Ảnh quá sáng hoặc bị lóa sáng (độ sáng trung bình: {mean_val:.1f}/255).")

    # 2. Kiểm tra độ sắc nét / độ mờ (Laplacian variance)
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if lap_var < 50.0:
        canh_bao.append(f"Ảnh bị mờ nét (độ sắc nét Laplacian: {lap_var:.1f} < 50). Hãy giữ chắc máy ảnh khi chụp.")

    # 3. Kiểm tra độ tương phản (độ lệch chuẩn mức xám)
    std_val = float(np.std(gray))
    if std_val < 20.0:
        canh_bao.append(f"Ảnh có độ tương phản quá thấp (độ lệch chuẩn: {std_val:.1f} < 20).")

    return True, canh_bao


def loai_bo_bong_do_va_can_bang_sang(
    anh_gray: np.ndarray,
    clip_limit: float = 2.0,
    ksize_dilate: int = 19,
    ksize_blur: int = 25
) -> np.ndarray:
    """
    Loại bỏ bóng đổ và cân bằng sáng bằng phương pháp ước lượng nền hình thái học (Background division / compensation)
    kết hợp CLAHE.

    Args:
        anh_gray: Ảnh mức xám 1 kênh uint8.
        clip_limit: Ngưỡng clip limit cho CLAHE (nếu > 0).
        ksize_dilate: Kích thước kernel phép giãn ước lượng nền sáng.
        ksize_blur: Kích thước kernel median blur làm mịn nền sáng.

    Returns:
        np.ndarray: Ảnh xám đã loại bỏ bóng đổ và cân bằng sáng.
    """
    if len(anh_gray.shape) == 3:
        anh_gray = chuyen_grayscale(anh_gray)

    # Đảm bảo kernel lẻ
    if ksize_dilate % 2 == 0:
        ksize_dilate += 1
    if ksize_blur % 2 == 0:
        ksize_blur += 1

    # Ước lượng nền bằng giãn hình ảnh + làm mịn trung vị
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (ksize_dilate, ksize_dilate))
    dilated = cv2.dilate(anh_gray, kernel)
    bg = cv2.medianBlur(dilated, ksize_blur)

    # Khử bóng đổ: sai khác so với nền
    diff = 255 - cv2.absdiff(anh_gray, bg)
    norm = cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)

    if clip_limit > 0:
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
        norm = clahe.apply(norm)

    return norm


def khu_nhieu(anh_gray: np.ndarray) -> np.ndarray:
    """
    Khử nhiễu muối tiêu và làm mịn nhẹ các biến dạng nén JPEG bằng Bilateral Filter.

    Args:
        anh_gray: Ảnh mức xám.

    Returns:
        np.ndarray: Ảnh xám đã khử nhiễu nhưng vẫn bảo tồn các đường cạnh sắc.
    """
    if len(anh_gray.shape) == 3:
        anh_gray = chuyen_grayscale(anh_gray)
    return cv2.bilateralFilter(anh_gray, d=5, sigmaColor=40, sigmaSpace=40)

