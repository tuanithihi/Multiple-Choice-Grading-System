"""
webcam.py – Chụp ảnh bài làm học sinh từ camera (webcam USB hoặc camera IP điện thoại).

Hỗ trợ toàn diện:
    - Camera USB / webcam tích hợp máy tính (index 0, 1, 2…).
    - Camera điện thoại kết nối qua cáp USB (DroidCam USB, Iriun Webcam, Camo...).
    - Camera IP qua mạng Wi-Fi (URL stream: DroidCam, IP Webcam, v.v.).
    - Tự động kiểm tra chất lượng & tính hợp lệ của phiếu ngay khi chụp:
        + Nếu KHÔNG ĐỦ ĐIỀU KIỆN: cảnh báo lý do (mờ, mất góc, bóng đổ) và yêu cầu chụp lại.
        + Nếu HỢP LỆ: lưu bài làm, hiển thị thumbnail bài đã nắn và sẵn sàng chụp tiếp bài sau.
    - HỖ TRỢ CHỤP LIÊN TỤC NHIỀU BÀI: Người dùng lật bài và bấm SPACE liên tục cho cả lớp.
    - Xoay ảnh 90° / 180° / 270° & Lật gương khi gắn điện thoại trên giá đỡ.
    - Khung ngắm định vị phiếu trắc nghiệm A4 tự động căn chỉnh.
    - Hướng dẫn kết nối điện thoại chi tiết từng bước tích hợp sẵn.
"""

import os
import sys
import time
import threading
import socket
from urllib.parse import urlparse
from typing import Callable, Optional

# Tắt log cảnh báo ồn ào của OpenCV trên Windows (obsensor / libavdevice)
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
import cv2
try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
except Exception:
    pass

import numpy as np
from PIL import Image, ImageTk

import tkinter as tk
from tkinter import ttk, messagebox


# ============================================================================
# CÁC HÀM TIỆN ÍCH KIỂM TRA & QUÉT CAMERA
# ============================================================================

def kiem_tra_ket_noi_tcp(url: str, timeout_sec: float = 1.5) -> bool:
    """
    Kiểm tra nhanh kết nối TCP tới địa chỉ IP và cổng của camera trước khi mở VideoCapture.
    Tránh trường hợp OpenCV bị treo/chờ timeout 20-30 giây khi máy chủ chưa bật.
    """
    try:
        p = urlparse(url)
        host = p.hostname
        if not host:
            return False
        port = p.port or (443 if p.scheme == "https" else 80)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout_sec)
        res = sock.connect_ex((host, port))
        sock.close()
        return res == 0
    except Exception:
        return False


def mo_camera_an_toan(nguon: int | str, chieu_rong: int = 1920, chieu_cao: int = 1080) -> Optional[cv2.VideoCapture]:
    """
    Mở thiết bị camera (USB index hoặc URL IP) an toàn với cơ chế thử nghiệm đa backend.

    Args:
        nguon: int (chỉ số camera USB) hoặc str (URL stream IP).
        chieu_rong: Độ phân giải chiều rộng mong muốn.
        chieu_cao: Độ phân giải chiều cao mong muốn.

    Returns:
        VideoCapture đã mở thành công hoặc None nếu thất bại.
    """
    if isinstance(nguon, str):
        # Mở camera IP qua URL stream
        url = nguon.strip()
        if not url:
            return None
        # Kiểm tra nhanh kết nối TCP (tránh chờ timeout OpenCV quá lâu nếu IP sai)
        if not kiem_tra_ket_noi_tcp(url, timeout_sec=1.5):
            return None
        try:
            cap = cv2.VideoCapture(url)
            if cap.isOpened():
                return cap
        except Exception:
            return None
        return None

    # Mở camera USB theo index
    idx = int(nguon)
    # Thử lần lượt các backend trên Windows: CAP_ANY -> CAP_DSHOW -> CAP_MSMF
    cac_backend = [cv2.CAP_ANY, cv2.CAP_DSHOW, cv2.CAP_MSMF]
    for backend in cac_backend:
        try:
            cap = cv2.VideoCapture(idx, backend) if backend != cv2.CAP_ANY else cv2.VideoCapture(idx)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, chieu_rong)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, chieu_cao)
                return cap
        except Exception:
            continue
    return None


def kiem_tra_camera(camera_index: int = 0) -> bool:
    """
    Kiểm tra xem camera/webcam có khả dụng và đọc được khung hình hay không.
    """
    try:
        cap = mo_camera_an_toan(camera_index, 640, 480)
        if cap is None:
            return False
        ret, frame = cap.read()
        cap.release()
        return bool(ret and frame is not None and frame.size > 0)
    except Exception:
        return False


def liet_ke_camera_co_san(max_index: int = 4) -> list[dict]:
    """
    Quét nhanh các camera USB/webcam/ảo (DroidCam, Iriun) có sẵn trên máy.

    Returns:
        Danh sách dict {"index": int, "name": str} cho mỗi camera khả dụng.
    """
    ket_qua = []
    for idx in range(max_index):
        try:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    label = f"Camera {idx}"
                    if idx == 0:
                        label += " (Mặc định / Tích hợp)"
                    else:
                        label += " (USB / Ngoại vi / DroidCam)"
                    label += f" - {w}x{h}"
                    ket_qua.append({"index": idx, "name": label})
                cap.release()
        except Exception:
            continue

    # Nếu không tìm thấy camera nào từ vòng quét, vẫn gợi ý Camera 0 và Camera 1
    if not ket_qua:
        ket_qua.append({"index": 0, "name": "Camera 0 (Thiết bị chính)"})
        ket_qua.append({"index": 1, "name": "Camera 1 (Ngoại vi / DroidCam USB)"})

    return ket_qua


def kiem_tra_camera_ip(url: str, timeout_ms: int = 4000) -> bool:
    """
    Kiểm tra xem URL stream camera IP có hoạt động và đọc được hình không.
    """
    url = (url or "").strip()
    if not url:
        return False
    if not kiem_tra_ket_noi_tcp(url, timeout_sec=1.5):
        return False
    try:
        cap = cv2.VideoCapture(url)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_ms)
        if not cap.isOpened():
            return False
        ret, frame = cap.read()
        cap.release()
        return bool(ret and frame is not None and frame.size > 0)
    except Exception:
        return False


# ============================================================================
# HÀM KIỂM TRA ĐIỀU KIỆN PHIẾU TRẢ LỜI NGAY KHI CHỤP
# ============================================================================

def kiem_tra_phieu_hop_le(anh: np.ndarray) -> tuple[bool, str, Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Kiểm tra xem ảnh vừa chụp từ camera có đủ điều kiện làm bài thi hay không.
    Điều kiện:
        1. Ảnh có độ nét và ánh sáng cơ bản (không bị mờ nhoè, không quá tối).
        2. Tìm thấy 4 góc phiếu / 4 marker chuẩn.
        3. Nắn phối cảnh (perspective warp) thành công.

    Returns:
        tuple (hop_le: bool, ly_do: str, pts_4_goc, anh_warped)
    """
    try:
        from omr.warp import xu_ly_va_nan_phieu
        from omr.detect_sheet import LoiKhongTimThayPhieu

        warped, pts_goc, phuong_phap = xu_ly_va_nan_phieu(anh)
        return True, f"Phát hiện phiếu hợp lệ ({phuong_phap})", pts_goc, warped
    except Exception as e:
        msg = str(e)
        if "LoiKhongTimThayPhieu" in type(e).__name__ or "Không tìm thấy" in msg:
            ly_do = "Không tìm thấy đủ 4 góc phiếu (phiếu bị lệch, lọt ra ngoài khung hình hoặc bị che khuất mép giấy)."
        elif "quá mờ" in msg or "mờ" in msg:
            ly_do = "Ảnh bị mờ hoặc rung tay khi chụp. Vui lòng giữ chắc camera và lấy nét."
        elif "quá tối" in msg or "tối" in msg:
            ly_do = "Ảnh quá tối hoặc bị bóng đổ của người/điện thoại che khuất bài làm."
        elif "cháy sáng" in msg or "quá sáng" in msg:
            ly_do = "Ảnh bị chói sáng hoặc phản chiếu ánh đèn mạnh lên mặt phiếu."
        else:
            ly_do = f"Phiếu chưa đạt chuẩn nhận diện: {msg}"
        return False, ly_do, None, None


# ============================================================================
# HƯỚNG DẪN KẾT NỐI ĐIỆN THOẠI
# ============================================================================

def hien_thi_huong_dan_ket_noi(parent: Optional[tk.Widget] = None) -> None:
    """Mở hộp thoại hướng dẫn chi tiết cách kết nối camera điện thoại với máy tính."""
    dlg = tk.Toplevel(parent)
    dlg.title("Hướng dẫn kết nối camera điện thoại")
    dlg.geometry("720x580")
    dlg.minsize(620, 460)
    if parent:
        dlg.transient(parent)

    main_f = ttk.Frame(dlg, padding=16)
    main_f.pack(fill=tk.BOTH, expand=True)

    ttk.Label(
        main_f,
        text="HƯỚNG DẪN DÙNG ĐIỆN THOẠI LÀM CAMERA CHỤP PHIẾU",
        font=("Segoe UI", 12, "bold"),
        foreground="#1e3a8a",
    ).pack(pady=(0, 10))

    canvas = tk.Canvas(main_f, borderwidth=0, highlightthickness=0)
    sb = ttk.Scrollbar(main_f, orient=tk.VERTICAL, command=canvas.yview)
    box = ttk.Frame(canvas)
    box.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=box, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    sb.pack(side=tk.RIGHT, fill=tk.Y)

    huong_dan_text = """
CÁCH 1: KẾT NỐI QUA CÁP USB (Khuyên dùng - Hình ảnh nét, cực mượt, không giật lag)
----------------------------------------------------------------------------------
1. Tải phần mềm DroidCam Client trên máy tính (tại https://www.dev47apps.com).
2. Tải ứng dụng DroidCam trên điện thoại (Google Play hoặc App Store).
3. Bật chế độ "Gỡ lỗi USB" (USB Debugging) trên điện thoại và cắm cáp USB vào máy tính.
4. Mở DroidCam trên cả điện thoại và máy tính, chọn biểu tượng [USB] rồi bấm "Start".
5. Trên phần mềm chấm thi:
   - Chọn mục "Camera USB / DroidCam USB".
   - Chọn Camera 1 hoặc 2 (tên DroidCam) trong danh sách và bấm "Mở camera".

CÁCH 2: KẾT NỐI QUA MẠNG WI-FI (Không cần dây cáp)
----------------------------------------------------------------------------------
A. Dùng DroidCam (Wi-Fi):
   1. Đảm bảo điện thoại và máy tính kết nối CÙNG một mạng Wi-Fi.
   2. Mở app DroidCam trên điện thoại, nhìn dòng: "WiFi IP: 192.168.1.X" và "Port: 4747".
   3. Trên phần mềm chấm thi:
      - Chọn "Camera IP (Wi-Fi)".
      - Nhập URL: http://<WiFi-IP>:4747/video (Ví dụ: http://192.168.1.15:4747/video).
      - Bấm "Kết nối".

B. Dùng ứng dụng "IP Webcam" (Android):
   1. Tải app "IP Webcam" trên Google Play.
   2. Mở app, kéo xuống dưới cùng chọn "Start server".
   3. Nhìn địa chỉ hiển thị dưới đáy màn hình điện thoại (thường dạng http://192.168.1.X:8080).
   4. Trên phần mềm chấm thi:
      - Nhập URL: http://<IP>:8080/video (Ví dụ: http://192.168.1.15:8080/video).
      - Bấm "Kết nối".

CÁCH 3: DÙNG IRIUN WEBCAM (Rất dễ dùng)
----------------------------------------------------------------------------------
1. Cài app Iriun Webcam trên cả máy tính (iriun.com) và điện thoại.
2. Mở app trên cả 2 thiết bị. Chúng sẽ tự động tìm thấy nhau qua Wi-Fi hoặc USB.
3. Phần mềm chấm thi sẽ tự nhận diện điện thoại như một webcam USB bình thường.

CÁCH CHỤP NHIỀU BÀI LIÊN TỤC VÀ KIỂM TRA ĐIỀU KIỆN:
----------------------------------------------------------------------------------
1. Bạn có thể chụp hàng chục bài thi liên tiếp mà không cần đóng cửa sổ camera.
2. Mỗi lần lật bài của học sinh xuống bàn, nhấn phím SPACE (hoặc bấm nút CHỤP BÀI LÀM).
3. Phần mềm sẽ TỰ ĐỘNG KIỂM TRA:
   - Nếu phiếu HỢP LỆ (đủ 4 góc, rõ nét): Nhận bài, tăng bộ đếm số bài và lưu file.
   - Nếu KHÔNG ĐỦ ĐIỀU KIỆN (bị mờ, lệch góc, bóng đổ): Sẽ báo lỗi cụ thể và yêu cầu chụp lại.
     Bạn chỉ cần kéo lại phiếu ngay ngắn và bấm SPACE chụp lại ngay!
4. Sau khi chụp xong cả lớp, bấm "Hoàn tất & Đóng (ESC)" để chuyển sang BƯỚC 3 chấm điểm.
"""

    txt = tk.Text(box, wrap=tk.WORD, font=("Consolas", 10), width=82, height=23, padx=10, pady=8)
    txt.insert(tk.END, huong_dan_text.strip())
    txt.configure(state=tk.DISABLED, bg="#f8fafc", fg="#1e293b", relief=tk.FLAT)
    txt.pack(fill=tk.BOTH, expand=True)

    btn_f = ttk.Frame(dlg, padding=(0, 8, 16, 8))
    btn_f.pack(fill=tk.X)
    ttk.Button(btn_f, text="Đã hiểu & Đóng", command=dlg.destroy).pack(side=tk.RIGHT)


# ============================================================================
# CỬA SỔ CHỤP ẢNH TỪ CAMERA (TKINTER NÂNG CAO – HỖ TRỢ CHỤP NHIỀU BÀI & VALIDATION)
# ============================================================================

class CuaSoChupAnh(tk.Toplevel):
    """
    Cửa sổ Tkinter xem trực tiếp (Live Preview) từ Camera USB hoặc Camera IP điện thoại.
    Hỗ trợ:
        - Kiểm tra tính hợp lệ của phiếu ngay khi chụp: nếu không đủ điều kiện sẽ báo và yêu cầu chụp lại.
        - Chụp nhiều bài liên tục (multi-sheet continuous capture) mà không bị gián đoạn.
        - Xoay hình 90/180/270 độ, lật gương, căn chỉnh khung ngắm A4.
        - Hiển thị thumbnail xem trước của phiếu vừa nắn thành công.
    """

    def __init__(
        self,
        parent: tk.Widget,
        thu_muc_luu: str = "outputs",
        camera_index: int = 0,
        camera_ip_url: str = "",
        on_chup_xong: Optional[Callable[[str], None]] = None,
    ):
        """
        Args:
            parent: Widget cha (cửa sổ chính).
            thu_muc_luu: Thư mục lưu file ảnh chụp bài làm.
            camera_index: Chỉ số camera USB ban đầu.
            camera_ip_url: URL camera IP ban đầu (nếu có).
            on_chup_xong: Callback được gọi mỗi khi chụp thành công 1 bài làm, nhận path file ảnh.
        """
        super().__init__(parent)
        self.title("Chụp ảnh bài làm từ Camera / Điện thoại (Hỗ trợ chụp nhiều bài)")
        self.geometry("1060x760")
        self.minsize(820, 580)
        self.transient(parent)

        self.thu_muc_luu = thu_muc_luu
        self.on_chup_xong = on_chup_xong

        # Trạng thái thiết bị & xử lý ảnh
        self.che_do_nguon = tk.StringVar(value="ip" if (camera_ip_url and camera_ip_url.strip()) else "usb")
        self.var_camera_usb_idx = tk.IntVar(value=camera_index)
        self.var_camera_ip_url = tk.StringVar(value=camera_ip_url.strip())
        self.goc_xoay = 0          # 0, 90, 180, 270 độ
        self.lat_guong = False     # Lật ngang
        self.var_kiem_tra_hop_le = tk.BooleanVar(value=True)  # Mặc định tự động kiểm tra phiếu

        # Luồng video & ảnh hiện tại
        self._cap: Optional[cv2.VideoCapture] = None
        self._dang_chay = False
        self._lock = threading.Lock()
        self._frame_raw: Optional[np.ndarray] = None
        self._photo_cache = None
        self._photo_thumb_cache = None

        # Thống kê phiên chụp
        self._so_bai_da_chup = 0
        self._so_lan_chup_lai = 0
        self._ds_file_da_chup: list[str] = []
        self._hieu_ung_flash = 0   # >0: flash xanh (thành công), <0: flash đỏ (không đạt)

        os.makedirs(self.thu_muc_luu, exist_ok=True)

        self._tao_giao_dien()

        # Ràng buộc phím tắt
        self.bind("<space>", lambda e: self._thuc_hien_chup())
        self.bind("<Return>", lambda e: self._thuc_hien_chup())
        self.bind("<r>", lambda e: self._xoay_anh())
        self.bind("<R>", lambda e: self._xoay_anh())
        self.bind("<Escape>", lambda e: self._dong_cua_so())
        self.protocol("WM_DELETE_WINDOW", self._dong_cua_so)

        # Bắt đầu kết nối nguồn ban đầu
        self.after(100, self._ket_noi_nguon_hien_tai)

        self.focus_force()
        try:
            self.grab_set()
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # XÂY DỰNG GIAO DIỆN
    # -------------------------------------------------------------------------
    def _tao_giao_dien(self) -> None:
        # 1. Thanh điều khiển nguồn camera phía trên
        panel_top = ttk.LabelFrame(self, text=" CẤU HÌNH NGUỒN CAMERA & ĐIỆN THOẠI ", padding=8)
        panel_top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(6, 4))

        # Hàng 1: Chọn chế độ nguồn (USB hay IP) & Nút Trợ giúp
        row1 = ttk.Frame(panel_top)
        row1.pack(fill=tk.X, pady=(0, 6))

        rb_usb = ttk.Radiobutton(
            row1,
            text="Camera USB / Máy tính / DroidCam USB",
            variable=self.che_do_nguon,
            value="usb",
            command=self._on_doi_che_do_nguon,
        )
        rb_usb.pack(side=tk.LEFT, padx=(0, 15))

        rb_ip = ttk.Radiobutton(
            row1,
            text="Camera IP / Điện thoại qua Wi-Fi",
            variable=self.che_do_nguon,
            value="ip",
            command=self._on_doi_che_do_nguon,
        )
        rb_ip.pack(side=tk.LEFT, padx=(0, 15))

        btn_help = ttk.Button(
            row1,
            text="Hướng dẫn kết nối điện thoại (?)",
            command=lambda: hien_thi_huong_dan_ket_noi(self),
        )
        btn_help.pack(side=tk.RIGHT)

        # Hàng 2: Chi tiết nguồn đang chọn
        self.frame_nguon_chi_tiet = ttk.Frame(panel_top)
        self.frame_nguon_chi_tiet.pack(fill=tk.X, pady=2)

        # Container cho nguồn USB
        self.box_usb = ttk.Frame(self.frame_nguon_chi_tiet)
        ttk.Label(self.box_usb, text="Thiết bị:").pack(side=tk.LEFT, padx=(0, 6))

        self.cb_danh_sach_usb = ttk.Combobox(self.box_usb, state="readonly", width=36)
        self.cb_danh_sach_usb.pack(side=tk.LEFT, padx=(0, 6))
        self.cb_danh_sach_usb.bind("<<ComboboxSelected>>", self._on_chon_camera_usb_cb)

        btn_quet = ttk.Button(self.box_usb, text="Quét lại camera", command=self._quet_lai_camera_usb)
        btn_quet.pack(side=tk.LEFT, padx=2)

        btn_ket_noi_usb = ttk.Button(self.box_usb, text="Mở camera", command=self._ket_noi_nguon_hien_tai)
        btn_ket_noi_usb.pack(side=tk.LEFT, padx=4)

        # Container cho nguồn IP
        self.box_ip = ttk.Frame(self.frame_nguon_chi_tiet)
        ttk.Label(self.box_ip, text="URL Stream:").pack(side=tk.LEFT, padx=(0, 6))

        self.entry_ip_url = ttk.Combobox(
            self.box_ip,
            textvariable=self.var_camera_ip_url,
            width=36,
            values=[
                "http://192.168.1.15:4747/video",
                "http://192.168.1.15:8080/video",
                "http://192.168.1.10:4747/video",
                "http://192.168.1.10:8080/video",
            ],
        )
        self.entry_ip_url.pack(side=tk.LEFT, padx=(0, 6))

        btn_ket_noi_ip = ttk.Button(self.box_ip, text="Kết nối", command=self._ket_noi_nguon_hien_tai)
        btn_ket_noi_ip.pack(side=tk.LEFT, padx=2)

        ttk.Label(
            self.box_ip,
            text="(DroidCam: :4747/video | IP Webcam: :8080/video)",
            font=("Segoe UI", 8),
            foreground="#64748b",
        ).pack(side=tk.LEFT, padx=6)

        # Cập nhật hiển thị hộp nguồn
        self._cap_nhat_view_nguon()
        self._quet_lai_camera_usb(cap_nhat_chon=False)

        # Hàng 3: Thanh công cụ điều khiển khung hình & Nút chụp
        panel_actions = ttk.Frame(self, padding=(10, 4))
        panel_actions.pack(side=tk.TOP, fill=tk.X)

        self.btn_xoay = ttk.Button(panel_actions, text="Xoay 90° (R)", command=self._xoay_anh)
        self.btn_xoay.pack(side=tk.LEFT, padx=2)

        self.btn_lat = ttk.Button(panel_actions, text="Lật gương", command=self._lat_guong_anh)
        self.btn_lat.pack(side=tk.LEFT, padx=2)

        self.lbl_goc_xoay = ttk.Label(panel_actions, text="Góc: 0°", font=("Segoe UI", 9, "bold"))
        self.lbl_goc_xoay.pack(side=tk.LEFT, padx=6)

        # Tùy chọn kiểm tra tự động phiếu khi chụp
        cb_val = ttk.Checkbutton(
            panel_actions,
            text="Tự động kiểm tra điều kiện phiếu khi chụp",
            variable=self.var_kiem_tra_hop_le,
        )
        cb_val.pack(side=tk.LEFT, padx=10)

        # Nút Đóng bên phải
        btn_dong = ttk.Button(panel_actions, text="Hoàn tất & Đóng (ESC)", command=self._dong_cua_so)
        btn_dong.pack(side=tk.RIGHT, padx=4)

        # Nút Chụp chính (Nổi bật, to)
        self.btn_chup = ttk.Button(
            panel_actions,
            text="CHỤP BÀI LÀM (SPACE)",
            command=self._thuc_hien_chup,
            style="Success.TButton",
        )
        self.btn_chup.pack(side=tk.RIGHT, padx=8)

        # 2. Vùng nội dung chính: Canvas Live Preview (Bên trái) + Sidebar trạng thái (Bên phải)
        main_content = ttk.Frame(self, padding=(10, 2))
        main_content.pack(fill=tk.BOTH, expand=True)

        # Bên trái: Canvas Video Preview
        self.frame_canvas = ttk.Frame(main_content)
        self.frame_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.frame_canvas, bg="#0f172a", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Bên phải: Sidebar hiển thị kết quả & thumbnail bài đã nắn
        self.frame_sidebar = ttk.LabelFrame(main_content, text=" TIẾN ĐỘ CHỤP BÀI THI ", padding=8, width=230)
        self.frame_sidebar.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
        self.frame_sidebar.pack_propagate(False)

        # Các nhãn đếm số lượng
        f_counts = ttk.Frame(self.frame_sidebar)
        f_counts.pack(fill=tk.X, pady=(0, 6))

        self.lbl_dem_bai = ttk.Label(
            f_counts,
            text="Đã đạt: 0 bài",
            font=("Segoe UI", 11, "bold"),
            foreground="#166534",
        )
        self.lbl_dem_bai.pack(anchor="w")

        self.lbl_dem_loi = ttk.Label(
            f_counts,
            text="Chụp lại: 0 lần",
            font=("Segoe UI", 9),
            foreground="#b45309",
        )
        self.lbl_dem_loi.pack(anchor="w", pady=(2, 0))

        ttk.Separator(self.frame_sidebar, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

        # Vùng xem trước thumbnail ảnh nắn bài gần nhất
        ttk.Label(
            self.frame_sidebar,
            text="Ảnh bài vừa chụp hợp lệ:",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")

        self.lbl_thumb = ttk.Label(
            self.frame_sidebar,
            text="Chưa có bài nào\n(Nhấn SPACE để chụp)",
            anchor="center",
            justify="center",
            background="#1e293b",
            foreground="#94a3b8",
            relief=tk.RIDGE,
        )
        self.lbl_thumb.pack(fill=tk.X, pady=6, ipady=40)

        # Lời nhắc chụp nhiều bài
        f_hint = ttk.Frame(self.frame_sidebar)
        f_hint.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        ttk.Label(
            f_hint,
            text="Mẹo chụp cả lớp:\n• Đặt lần lượt từng bài\n• Nhấn phím SPACE để chụp\n• Nếu lỗi -> phần mềm sẽ báo chụp lại\n• Chụp xong bấm Hoàn tất.",
            font=("Segoe UI", 8),
            foreground="#475569",
            justify=tk.LEFT,
        ).pack(anchor="w")

        # 3. Thanh trạng thái dưới cùng
        status_f = ttk.Frame(self, padding=(10, 4), relief=tk.SUNKEN)
        status_f.pack(side=tk.BOTTOM, fill=tk.X)

        self.var_trang_thai = tk.StringVar(value="Đang khởi tạo camera...")
        self.lbl_msg = ttk.Label(status_f, textvariable=self.var_trang_thai, font=("Segoe UI", 9))
        self.lbl_msg.pack(side=tk.LEFT)

        self.lbl_fps_res = ttk.Label(status_f, text="", font=("Segoe UI", 8), foreground="#64748b")
        self.lbl_fps_res.pack(side=tk.RIGHT)

    # -------------------------------------------------------------------------
    # QUẢN LÝ NGUỒN & KẾT NỐI
    # -------------------------------------------------------------------------
    def _on_doi_che_do_nguon(self) -> None:
        self._cap_nhat_view_nguon()

    def _cap_nhat_view_nguon(self) -> None:
        """Chuyển đổi hiển thị giữa thanh chọn USB và ô nhập IP."""
        if self.che_do_nguon.get() == "usb":
            self.box_ip.pack_forget()
            self.box_usb.pack(fill=tk.X)
        else:
            self.box_usb.pack_forget()
            self.box_ip.pack(fill=tk.X)

    def _quet_lai_camera_usb(self, cap_nhat_chon: bool = True) -> None:
        """Quét các camera USB và đưa vào combobox."""
        cams = liet_ke_camera_co_san(max_index=4)
        ds_ten = [c["name"] for c in cams]
        self._ds_cam_usb_obj = cams
        self.cb_danh_sach_usb.configure(values=ds_ten)

        cur_idx = self.var_camera_usb_idx.get()
        chon_idx = 0
        for i, c in enumerate(cams):
            if c["index"] == cur_idx:
                chon_idx = i
                break

        if ds_ten:
            self.cb_danh_sach_usb.current(chon_idx)
            if cap_nhat_chon:
                self.var_camera_usb_idx.set(cams[chon_idx]["index"])

    def _on_chon_camera_usb_cb(self, event=None) -> None:
        sel_idx = self.cb_danh_sach_usb.current()
        if 0 <= sel_idx < len(getattr(self, "_ds_cam_usb_obj", [])):
            self.var_camera_usb_idx.set(self._ds_cam_usb_obj[sel_idx]["index"])

    def _ket_noi_nguon_hien_tai(self) -> None:
        """Bắt đầu kết nối nguồn đã chọn trên luồng nền để không đơ giao diện."""
        # Dừng nguồn cũ
        self._dung_camera()

        che_do = self.che_do_nguon.get()
        if che_do == "usb":
            nguon = self.var_camera_usb_idx.get()
            mo_ta = f"Camera USB {nguon}"
        else:
            nguon = self.var_camera_ip_url.get().strip()
            if not nguon:
                self.var_trang_thai.set("Vui lòng nhập URL camera IP (ví dụ http://192.168.1.5:4747/video)!")
                return
            mo_ta = f"Camera IP ({nguon})"

        self.var_trang_thai.set(f"Đang kết nối tới {mo_ta}...")
        self.btn_chup.configure(state=tk.DISABLED)

        # Mở camera trong background thread
        def _thread_connect():
            cap = mo_camera_an_toan(nguon)
            self.after(0, lambda: self._on_ket_noi_xong(cap, mo_ta))

        t = threading.Thread(target=_thread_connect, daemon=True)
        t.start()

    def _on_ket_noi_xong(self, cap: Optional[cv2.VideoCapture], mo_ta: str) -> None:
        """Xử lý sau khi kết nối xong."""
        if cap is None or not cap.isOpened():
            self.var_trang_thai.set(f"Không thể kết nối tới {mo_ta}. Kiểm tra lại cáp / mạng Wi-Fi!")
            self._ve_man_hinh_loi(f"Không kết nối được tới {mo_ta}\n\n- Với USB: Kiểm tra cáp cắm hoặc ứng dụng DroidCam Client.\n- Với Wi-Fi: Đảm bảo điện thoại và máy tính cùng mạng Wi-Fi.")
            self.btn_chup.configure(state=tk.DISABLED)
            return

        # Kiểm tra đọc thử frame đầu tiên
        ret, frame = cap.read()
        if not ret or frame is None:
            cap.release()
            self.var_trang_thai.set(f"Mở được {mo_ta} nhưng không đọc được dữ liệu hình ảnh!")
            self.btn_chup.configure(state=tk.DISABLED)
            return

        with self._lock:
            self._cap = cap
            self._dang_chay = True
            self._frame_raw = frame.copy()

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.lbl_fps_res.configure(text=f"Độ phân giải: {w}x{h}")
        self.var_trang_thai.set(f"Đã kết nối {mo_ta}. Căn chỉnh phiếu vào khung xanh và nhấn SPACE để chụp!")
        self.btn_chup.configure(state=tk.NORMAL)

        # Bắt đầu vòng lặp đọc và vẽ frame
        self._vong_lap_hien_thi()

    # -------------------------------------------------------------------------
    # VÒNG LẶP VIDEO & HIỂN THỊ
    # -------------------------------------------------------------------------
    def _vong_lap_hien_thi(self) -> None:
        """Đọc khung hình liên tục và vẽ lên Canvas."""
        if not self._dang_chay:
            return

        cap = self._cap
        if cap is None:
            return

        try:
            ret, frame = cap.read()
            if ret and frame is not None:
                with self._lock:
                    self._frame_raw = frame
                self._ve_frame_len_canvas(frame)
            else:
                self.var_trang_thai.set("Mất tín hiệu camera tạm thời...")
        except Exception as e:
            self.var_trang_thai.set(f"Lỗi đọc camera: {e}")

        # Lặp lại sau ~33ms (~30 FPS)
        self.after(33, self._vong_lap_hien_thi)

    def _ve_frame_len_canvas(self, frame: np.ndarray) -> None:
        """Xoay, lật, vẽ khung ngắm A4 và hiển thị lên Canvas."""
        # 1. Xoay và lật hình theo thiết lập của người dùng
        vis = frame.copy()
        if self.goc_xoay == 90:
            vis = cv2.rotate(vis, cv2.ROTATE_90_CLOCKWISE)
        elif self.goc_xoay == 180:
            vis = cv2.rotate(vis, cv2.ROTATE_180)
        elif self.goc_xoay == 270:
            vis = cv2.rotate(vis, cv2.ROTATE_90_COUNTERCLOCKWISE)

        if self.lat_guong:
            vis = cv2.flip(vis, 1)

        h, w = vis.shape[:2]

        # 2. Vẽ khung ngắm định vị phiếu A4
        vis = self._ve_khung_ngam_a4(vis)

        # Hiệu ứng flash thị giác khi vừa bấm chụp
        if self._hieu_ung_flash > 0:
            self._hieu_ung_flash -= 1
            # Lớp phủ xanh lá nhạt cho ảnh chụp hợp lệ
            overlay = np.zeros_like(vis)
            overlay[:, :] = (0, 255, 0)
            vis = cv2.addWeighted(vis, 0.65, overlay, 0.35, 0)
        elif self._hieu_ung_flash < 0:
            self._hieu_ung_flash += 1
            # Lớp phủ đỏ/cam cảnh báo không đạt điều kiện
            overlay = np.zeros_like(vis)
            overlay[:, :] = (0, 0, 255)
            vis = cv2.addWeighted(vis, 0.65, overlay, 0.35, 0)

        # 3. Chuyển đổi sang ImageTk và render
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w < 50 or canvas_h < 50:
            canvas_w, canvas_h = 750, 500

        scale = min(canvas_w / w, canvas_h / h)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))

        resized = cv2.resize(vis, (new_w, new_h), interpolation=cv2.INTER_AREA)
        rgb_img = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img)
        self._photo_cache = ImageTk.PhotoImage(pil_img)

        self.canvas.delete("all")
        x_off = (canvas_w - new_w) // 2
        y_off = (canvas_h - new_h) // 2
        self.canvas.create_image(x_off, y_off, anchor="nw", image=self._photo_cache)

    def _ve_khung_ngam_a4(self, vis: np.ndarray) -> np.ndarray:
        """Vẽ khung chữ nhật xanh lá tỉ lệ A4 đứng và các góc định vị."""
        h, w = vis.shape[:2]

        # Phiếu A4 tiêu chuẩn có tỉ lệ rộng / cao xấp xỉ 1 / 1.414 (hoặc 1055/1491 = 0.707)
        ti_le_a4 = 1055.0 / 1491.0
        if h >= w:
            box_h = int(h * 0.88)
            box_w = int(box_h * ti_le_a4)
            if box_w > w * 0.95:
                box_w = int(w * 0.92)
                box_h = int(box_w / ti_le_a4)
        else:
            box_h = int(h * 0.90)
            box_w = int(box_h * ti_le_a4)

        x1 = max(0, (w - box_w) // 2)
        y1 = max(0, (h - box_h) // 2)
        x2 = min(w, x1 + box_w)
        y2 = min(h, y1 + box_h)

        # Khung viền mỏng
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # 4 góc định vị đậm nét
        corner_len = max(20, int(min(w, h) * 0.04))
        c_color = (0, 240, 255)
        thickness = 4

        # Trên-trái
        cv2.line(vis, (x1, y1), (x1 + corner_len, y1), c_color, thickness)
        cv2.line(vis, (x1, y1), (x1, y1 + corner_len), c_color, thickness)
        # Trên-phải
        cv2.line(vis, (x2, y1), (x2 - corner_len, y1), c_color, thickness)
        cv2.line(vis, (x2, y1), (x2, y1 + corner_len), c_color, thickness)
        # Dưới-trái
        cv2.line(vis, (x1, y2), (x1 + corner_len, y2), c_color, thickness)
        cv2.line(vis, (x1, y2), (x1, y2 - corner_len), c_color, thickness)
        # Dưới-phải
        cv2.line(vis, (x2, y2), (x2 - corner_len, y2), c_color, thickness)
        cv2.line(vis, (x2, y2), (x2 - corner_len, y2), c_color, thickness)

        # Dòng nhắc nhở trên cùng của khung
        cv2.putText(
            vis,
            "DAT PHIEU VAO KHUNG XANH | NHAN SPACE DE CHUP",
            (max(10, x1 + 10), max(25, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 0),
            2,
        )

        return vis

    def _ve_man_hinh_loi(self, thong_diep: str) -> None:
        """Vẽ màn hình thông báo thân thiện lên canvas khi chưa có hình."""
        self.canvas.delete("all")
        w = max(200, self.canvas.winfo_width())
        h = max(200, self.canvas.winfo_height())
        self.canvas.create_rectangle(0, 0, w, h, fill="#0f172a", outline="")
        self.canvas.create_text(
            w // 2,
            h // 2,
            text=thong_diep,
            fill="#e2e8f0",
            font=("Segoe UI", 11),
            justify=tk.CENTER,
        )

    # -------------------------------------------------------------------------
    # XOAY & LẬT ẢNH
    # -------------------------------------------------------------------------
    def _xoay_anh(self) -> None:
        """Xoay khung hình theo chiều kim đồng hồ mỗi lần 90 độ."""
        self.goc_xoay = (self.goc_xoay + 90) % 360
        self.lbl_goc_xoay.configure(text=f"Góc: {self.goc_xoay}°")
        self.var_trang_thai.set(f"Đã xoay ảnh sang {self.goc_xoay}°.")

    def _lat_guong_anh(self) -> None:
        """Lật ảnh ngang."""
        self.lat_guong = not self.lat_guong
        trang_thai_lat = "BẬT" if self.lat_guong else "TẮT"
        self.var_trang_thai.set(f"Lật gương: {trang_thai_lat}.")

    def _cap_nhat_preview_warped(self, warped_img: np.ndarray) -> None:
        """Cập nhật ảnh thumbnail bài thi vừa được nắn thẳng lên sidebar."""
        try:
            # Resize về kích thước thumbnail ~140x198 px
            thumb_h = 198
            thumb_w = 140
            rgb_warped = cv2.cvtColor(warped_img, cv2.COLOR_BGR2RGB) if len(warped_img.shape) == 3 else cv2.cvtColor(warped_img, cv2.COLOR_GRAY2RGB)
            resized = cv2.resize(rgb_warped, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
            pil_thumb = Image.fromarray(resized)
            self._photo_thumb_cache = ImageTk.PhotoImage(pil_thumb)
            self.lbl_thumb.configure(image=self._photo_thumb_cache, text="")
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # HÀNH ĐỘNG CHỤP ẢNH & KIỂM TRA ĐIỀU KIỆN
    # -------------------------------------------------------------------------
    def _thuc_hien_chup(self) -> None:
        """
        Chụp khung hình hiện tại (đã áp dụng xoay/lật), kiểm tra tính hợp lệ của phiếu:
        - Nếu HỢP LỆ: Lưu file, cập nhật danh sách bài thi, báo thành công, sẵn sàng chụp tiếp bài sau.
        - Nếu KHÔNG HỢP LỆ: Báo không đủ điều kiện, giải thích lý do, yêu cầu chụp lại và KHÔNG lưu file lỗi.
        """
        with self._lock:
            if self._frame_raw is None:
                messagebox.showwarning(
                    "Chưa có hình",
                    "Camera chưa sẵn sàng hoặc chưa nhận được khung hình.",
                    parent=self,
                )
                return
            frame_chup = self._frame_raw.copy()

        # Áp dụng xoay & lật trước khi xử lý
        if self.goc_xoay == 90:
            frame_chup = cv2.rotate(frame_chup, cv2.ROTATE_90_CLOCKWISE)
        elif self.goc_xoay == 180:
            frame_chup = cv2.rotate(frame_chup, cv2.ROTATE_180)
        elif self.goc_xoay == 270:
            frame_chup = cv2.rotate(frame_chup, cv2.ROTATE_90_COUNTERCLOCKWISE)

        if self.lat_guong:
            frame_chup = cv2.flip(frame_chup, 1)

        # 1. KIỂM TRA TÍNH HỢP LỆ CỦA PHIẾU NẾU BẬT CHẾ ĐỘ KIỂM TRA
        warped_ket_qua = None
        if self.var_kiem_tra_hop_le.get():
            self.var_trang_thai.set("Đang kiểm tra chất lượng & định vị phiếu...")
            self.update_idletasks()

            hop_le, ly_do, pts_goc, warped = kiem_tra_phieu_hop_le(frame_chup)

            if not hop_le:
                # Hiệu ứng flash cảnh báo màu đỏ
                self._hieu_ung_flash = -2
                self._so_lan_chup_lai += 1
                self.lbl_dem_loi.configure(text=f"Chụp lại: {self._so_lan_chup_lai} lần")
                self.var_trang_thai.set(f"❌ KHÔNG ĐỦ ĐIỀU KIỆN: {ly_do} -> Hãy chụp lại!")

                # Hiển thị thông báo yêu cầu chụp lại
                messagebox.showwarning(
                    "Phiếu không đủ điều kiện",
                    f"⚠️ PHIẾU TRẢ LỜI KHÔNG ĐỦ ĐIỀU KIỆN CHẤM BÀI!\n\n"
                    f"Lý do nhận diện:\n{ly_do}\n\n"
                    f"YÊU CẦU CHỤP LẠI:\n"
                    f"1. Căn chỉnh phiếu trắc nghiệm nằm ngay ngắn bên trong khung màu xanh.\n"
                    f"2. Đảm bảo nhìn rõ cả 4 góc của phiếu (không bị thiếu góc / mất mép giấy).\n"
                    f"3. Giữ điện thoại cố định, đủ ánh sáng và tránh để bóng tay/điện thoại đè lên bài.\n\n"
                    f"👉 Hãy căn chỉnh lại bài làm và nhấn phím SPACE để chụp lại!",
                    parent=self,
                )
                # KHÔNG LƯU FILE LỖI VÀO DANH SÁCH BÀI LÀM
                return

            warped_ket_qua = warped

        # 2. PHIẾU HỢP LỆ -> LƯU FILE VÀ ĐƯA VÀO DANH SÁCH BÀI LÀM
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        self._so_bai_da_chup += 1
        ten_file = f"webcam_hs_{timestamp_str}_{self._so_bai_da_chup:02d}.jpg"
        duong_dan_luu = os.path.join(self.thu_muc_luu, ten_file)

        try:
            thanh_cong, buffer = cv2.imencode(
                ".jpg",
                frame_chup,
                [int(cv2.IMWRITE_JPEG_QUALITY), 95],
            )
            if thanh_cong:
                with open(duong_dan_luu, "wb") as f:
                    f.write(buffer)

                # Hiệu ứng flash xanh lá thị giác xác nhận thành công
                self._hieu_ung_flash = 2

                # Cập nhật số bài và danh sách
                self._ds_file_da_chup.append(duong_dan_luu)
                self.lbl_dem_bai.configure(text=f"Đã đạt: {self._so_bai_da_chup} bài")
                self.var_trang_thai.set(
                    f"✅ HỢP LỆ! Đã lưu bài số {self._so_bai_da_chup}: {ten_file} | 👉 Đặt bài tiếp theo và nhấn SPACE."
                )

                # Cập nhật ảnh thumbnail nếu có
                if warped_ket_qua is not None:
                    self._cap_nhat_preview_warped(warped_ket_qua)

                # Gọi callback thêm vào danh sách bài làm của giao diện chính
                if self.on_chup_xong:
                    self.on_chup_xong(duong_dan_luu)
            else:
                messagebox.showerror("Lỗi", "Không thể mã hóa ảnh JPEG để ghi file.", parent=self)
        except Exception as e:
            messagebox.showerror("Lỗi lưu ảnh", f"Không thể lưu file ảnh:\n{e}", parent=self)

    # -------------------------------------------------------------------------
    # ĐÓNG & DỌN DẸP TÀI NGUYÊN
    # -------------------------------------------------------------------------
    def _dung_camera(self) -> None:
        """Dừng video capture an toàn."""
        self._dang_chay = False
        with self._lock:
            if self._cap is not None:
                try:
                    self._cap.release()
                except Exception:
                    pass
                self._cap = None
            self._frame_raw = None

    def _dong_cua_so(self) -> None:
        """Dừng camera và đóng cửa sổ."""
        self._dung_camera()
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


# ============================================================================
# HÀM CHỤP WEBCAM DÒNG LỆNH (CLI & GIỮ TƯƠNG THÍCH CODE CŨ)
# ============================================================================

def chup_anh_tu_webcam(
    camera_index: int = 0,
    thu_muc_luu: str = "outputs",
    ten_file: Optional[str] = None,
    luu_duong_dan: Optional[str] = None,
    camera_ip_url: Optional[str] = None,
) -> Optional[str]:
    """
    Chụp ảnh từ webcam hoặc camera IP qua cửa sổ OpenCV (cv2.imshow).
    Dành cho chế độ dòng lệnh (CLI). Tự động kiểm tra tính hợp lệ của phiếu khi chụp.
    """
    if luu_duong_dan:
        thu_muc = os.path.dirname(luu_duong_dan) or "."
        os.makedirs(thu_muc, exist_ok=True)
    else:
        os.makedirs(thu_muc_luu, exist_ok=True)

    nguon = camera_ip_url.strip() if (camera_ip_url and camera_ip_url.strip()) else camera_index
    print(f"\n[CAMERA] Đang kết nối tới nguồn: {nguon}...")

    cap = mo_camera_an_toan(nguon)
    if cap is None or not cap.isOpened():
        print("[CAMERA] Không thể mở thiết bị camera.")
        print("  - Với USB: Kiểm tra cáp cắm hoặc ứng dụng DroidCam Client.")
        print("  - Với Camera IP: Kiểm tra lại địa chỉ URL stream và mạng Wi-Fi.")
        return None

    cua_so_ten = "OMR Camera - Nhan [SPACE] de chup | [R] xoay 90 do | [ESC] thoat"
    cv2.namedWindow(cua_so_ten, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(cua_so_ten, 960, 720)

    print("Camera đã sẵn sàng!")
    print("   - Đặt phiếu trắc nghiệm vào khung ngắm A4.")
    print("   - Nhấn [SPACE] để chụp ảnh bài làm.")
    print("   - Nhấn [R] để xoay ảnh 90 độ.")
    print("   - Nhấn [ESC] hoặc [Q] để thoát.")

    anh_da_chup = None
    goc_xoay = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("[CAMERA] Mất tín hiệu hình ảnh.")
                break

            # Áp dụng góc xoay
            vis = frame.copy()
            if goc_xoay == 90:
                vis = cv2.rotate(vis, cv2.ROTATE_90_CLOCKWISE)
            elif goc_xoay == 180:
                vis = cv2.rotate(vis, cv2.ROTATE_180)
            elif goc_xoay == 270:
                vis = cv2.rotate(vis, cv2.ROTATE_90_COUNTERCLOCKWISE)

            h, w = vis.shape[:2]

            # Khung ngắm A4
            box_h = int(h * 0.88)
            box_w = int(box_h * (1055.0 / 1491.0))
            x1 = max(0, (w - box_w) // 2)
            y1 = max(0, (h - box_h) // 2)
            x2 = min(w, x1 + box_w)
            y2 = min(h, y1 + box_h)

            cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
            corner_len = 30
            for (cx, cy), (dx, dy) in [
                ((x1, y1), (1, 1)), ((x2, y1), (-1, 1)),
                ((x1, y2), (1, -1)), ((x2, y2), (-1, -1)),
            ]:
                cv2.line(vis, (cx, cy), (cx + dx * corner_len, cy), (0, 220, 255), 4)
                cv2.line(vis, (cx, cy), (cx + dy * corner_len, cy), (0, 220, 255), 4)

            cv2.rectangle(vis, (0, h - 45), (w, h), (0, 0, 0), -1)
            cv2.putText(
                vis,
                f"[SPACE] Chup | [R] Xoay ({goc_xoay} deg) | [ESC] Thoat",
                (w // 2 - 240, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 255),
                2,
            )

            cv2.imshow(cua_so_ten, vis)
            key = cv2.waitKey(15) & 0xFF
            if key == 32:  # SPACE -> Kiểm tra tính hợp lệ
                hop_le, ly_do, pts, warped = kiem_tra_phieu_hop_le(vis)
                if not hop_le:
                    print(f"\n[CANH BAO] PHIẾU KHÔNG ĐỦ ĐIỀU KIỆN: {ly_do}")
                    print("          Vui lòng căn chỉnh lại phiếu ngay ngắn và nhấn [SPACE] để chụp lại!")
                else:
                    print(f"\n[THANH CONG] Phiếu hợp lệ! Đang lưu...")
                    anh_da_chup = vis.copy()
                    break
            elif key in (ord("r"), ord("R")):
                goc_xoay = (goc_xoay + 90) % 360
            elif key in (27, ord("q"), ord("Q")):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    if anh_da_chup is not None:
        if luu_duong_dan:
            duong_dan_luu = luu_duong_dan
        else:
            if not ten_file:
                timestamp_str = time.strftime("%Y%m%d_%H%M%S")
                ten_file = f"webcam_hs_{timestamp_str}.jpg"
            duong_dan_luu = os.path.join(thu_muc_luu, ten_file)

        thanh_cong, buffer = cv2.imencode(".jpg", anh_da_chup, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        if thanh_cong:
            with open(duong_dan_luu, "wb") as f:
                f.write(buffer)
            print(f"[CAMERA] Đã chụp và lưu thành công: {duong_dan_luu}")
            return duong_dan_luu
        else:
            print("[CAMERA] Lỗi ghi file ảnh chụp.")
            return None

    print("[CAMERA] Đã hủy chụp ảnh.")
    return None
