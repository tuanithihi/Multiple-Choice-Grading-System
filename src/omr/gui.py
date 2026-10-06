"""
gui.py – Giao diện đồ họa người dùng Tkinter cho hệ thống OMR chấm trắc nghiệm.

Cung cấp quy trình 3 bước trực quan:
    BƯỚC 1: ĐÁP ÁN MẪU – Chọn ảnh/thư mục đáp án mẫu, kiểm tra & sửa tay đáp án chuẩn.
    BƯỚC 2: BÀI LÀM HỌC SINH – Chọn ảnh, chọn thư mục, hoặc chụp trực tiếp từ webcam.
    BƯỚC 3: CHẤM & KẾT QUẢ – Chấm đa luồng (threading), hiển thị bảng điểm, xem ảnh gốc vs
             ảnh đã chấm, xem chi tiết 50 câu, sửa tay đáp án/mã đề/SBD và xuất Excel/SQLite.
"""

import os
import sys
import threading
import time
from typing import Any, Callable

import cv2
import numpy as np
from PIL import Image, ImageTk

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from omr.config import nap_config
from omr.samples import doc_anh_unicode, kiem_tra_anh, liet_ke_anh_thu_muc
from omr.warp import xu_ly_va_nan_phieu
from omr.read_sheet import read_sheet
from omr.answer_key import dung_tu_dien_dap_an, LoiDapAnMau
from omr.scoring import (
    cham_mot_bai,
    tinh_diem_50_cau,
    TRANG_THAI_DA_CHAM,
    TRANG_THAI_CHUA_CHAM,
    TRANG_THAI_LOI_ANH,
)
from omr.export import xuat_excel, xuat_sqlite
from omr.webcam import kiem_tra_camera, chup_anh_tu_webcam, CuaSoChupAnh, liet_ke_camera_co_san, kiem_tra_camera_ip


# =============================================================================
# CONTROLLER: QUẢN LÝ NGHIỆP VỤ & TRẠNG THÁI (ĐỘC LẬP VỚI GIAO DIỆN)
# =============================================================================

class OMRController:
    """
    Bộ điều khiển nghiệp vụ trung tâm (Business Controller) tách biệt khỏi giao diện Tkinter.
    Giúp kiểm thử tự động toàn diện mà không cần hiển thị cửa sổ đồ họa.
    """

    def __init__(self, config: dict | None = None):
        self.config = config if config is not None else nap_config()
        self.tu_dien_dap_an: dict[str, dict[str, Any]] = {}
        self.danh_sach_bai_lam: list[dict[str, Any]] = []
        self.danh_sach_ket_qua: list[dict[str, Any]] = []
        self.bai_hien_tai_idx: int = -1
        self.dang_cham: bool = False

    def nap_dap_an_tu_file(self, file_path: str, override_ma_de: str | None = None) -> tuple[bool, str]:
        """Nạp 1 file ảnh đáp án mẫu."""
        if not os.path.isfile(file_path):
            return False, f"Không tìm thấy file: {file_path}"
        try:
            res = read_sheet(file_path, config=self.config)
            ma_de = override_ma_de.strip() if override_ma_de else res.get("ma_de", "???")
            if not ma_de or "?" in ma_de or len(ma_de) != 3:
                # Nếu không đọc được mã đề, cho phép gán mã đề mặc định nếu chưa có
                if override_ma_de:
                    ma_de = override_ma_de
                else:
                    ma_de = "567"  # Mặc định gợi ý nếu ảnh mẫu để trống mã đề

            answers_50 = [a["lua_chon"] for a in res["answers"]]
            self.tu_dien_dap_an[ma_de] = {
                "ma_de": ma_de,
                "answers": answers_50,
                "answers_raw": res["answers"],
                "source_image": os.path.basename(file_path),
                "file_path": file_path,
                "warped": res.get("warped"),
            }
            return True, f"Đã nạp đáp án mẫu mã đề {ma_de} ({os.path.basename(file_path)})"
        except Exception as e:
            return False, f"Lỗi đọc ảnh đáp án mẫu: {e}"

    def nap_dap_an_tu_thu_muc(self, dir_path: str, override_ma_de: str | None = "567") -> tuple[bool, str]:
        """Nạp toàn bộ ảnh đáp án mẫu trong thư mục."""
        if not os.path.isdir(dir_path):
            return False, f"Thư mục không tồn tại: {dir_path}"
        try:
            tu_dien = dung_tu_dien_dap_an(
                dir_path,
                config=self.config,
                override_ma_de=override_ma_de
            )
            self.tu_dien_dap_an.update(tu_dien)
            so_luong = len(self.tu_dien_dap_an)
            return True, f"Đã nạp thành công {so_luong} mã đề đáp án chuẩn từ '{dir_path}'"
        except Exception as e:
            return False, f"Lỗi nạp thư mục đáp án mẫu: {e}"

    def cap_nhat_dap_an_chuan(self, ma_de: str, answers_list: list[str]) -> bool:
        """Cập nhật đáp án chuẩn của một mã đề do giáo viên sửa tay."""
        if ma_de in self.tu_dien_dap_an and len(answers_list) == 50:
            self.tu_dien_dap_an[ma_de]["answers"] = list(answers_list)
            return True
        return False

    def them_anh_bai_lam(self, file_path: str) -> tuple[bool, str]:
        """Thêm 1 ảnh bài làm của học sinh vào danh sách chờ chấm."""
        info = kiem_tra_anh(file_path)
        if not info["ton_tai"]:
            return False, f"Không tìm thấy file: {file_path}"
        # Kiểm tra trùng lặp đường dẫn
        for b in self.danh_sach_bai_lam:
            if b["duong_dan"] == file_path:
                return False, f"Ảnh đã có trong danh sách: {os.path.basename(file_path)}"
        self.danh_sach_bai_lam.append(info)
        return True, f"Đã thêm bài làm: {info['ten_file']}"

    def them_thu_muc_bai_lam(self, dir_path: str) -> tuple[int, str]:
        """Thêm toàn bộ ảnh bài làm từ thư mục."""
        if not os.path.isdir(dir_path):
            return 0, f"Thư mục không tồn tại: {dir_path}"
        ds_moi = liet_ke_anh_thu_muc(dir_path)
        da_them = 0
        cac_duong_dan_cu = {b["duong_dan"] for b in self.danh_sach_bai_lam}
        for item in ds_moi:
            if item["duong_dan"] not in cac_duong_dan_cu:
                self.danh_sach_bai_lam.append(item)
                da_them += 1
        return da_them, f"Đã nạp thêm {da_them} ảnh bài làm từ '{dir_path}'"

    def xoa_danh_sach_bai_lam(self) -> None:
        """Xóa sạch danh sách bài làm và kết quả cũ."""
        self.danh_sach_bai_lam.clear()
        self.danh_sach_ket_qua.clear()
        self.bai_hien_tai_idx = -1

    def cham_tat_ca(
        self,
        progress_cb: Callable[[int, int, str], None] | None = None
    ) -> list[dict[str, Any]]:
        """
        Chấm toàn bộ danh sách bài làm với đáp án chuẩn đã nạp.
        Hỗ trợ gọi hàm callback báo tiến độ (tiến_độ_hiện_tại, tổng_số, tên_file).
        """
        if not self.tu_dien_dap_an:
            raise ValueError("Chưa có đáp án mẫu chuẩn. Vui lòng nạp đáp án mẫu trước khi chấm bài.")

        if not self.danh_sach_bai_lam:
            return []

        self.dang_cham = True
        self.danh_sach_ket_qua.clear()
        tong = len(self.danh_sach_bai_lam)

        for idx, item in enumerate(self.danh_sach_bai_lam):
            ten_file = item["ten_file"]
            if progress_cb:
                progress_cb(idx + 1, tong, ten_file)

            if item["hop_le"]:
                res = cham_mot_bai(
                    item["duong_dan"],
                    tu_dien_dap_an=self.tu_dien_dap_an,
                    config=self.config
                )
            else:
                res = {
                    "sbd": "????",
                    "ma_de": "???",
                    "ma_de_goc": "???",
                    "so_dung": 0,
                    "so_sai": 0,
                    "so_blank": 0,
                    "so_multi": 0,
                    "so_ambiguous": 0,
                    "diem": 0.0,
                    "ma_de_khop": False,
                    "ten_anh_bai_lam": ten_file,
                    "ten_anh_dap_an": None,
                    "trang_thai": TRANG_THAI_LOI_ANH,
                    "ly_do": f"File không đọc được hoặc không hợp lệ: {item.get('loi', 'Lỗi file')}",
                    "chi_tiet_50_cau": [],
                    "warnings": [item.get("loi", "File hỏng")],
                    "file_path": item["duong_dan"],
                    "thoi_gian_xu_ly": 0.0,
                }

            self.danh_sach_ket_qua.append(res)

        # Phát hiện nghi trùng bài (cùng SBD + Mã đề)
        sbd_md_map: dict[tuple[str, str], list[int]] = {}
        for i, r in enumerate(self.danh_sach_ket_qua):
            sbd = r.get("sbd", "????")
            md = r.get("ma_de", "???")
            if sbd != "????" and md != "???" and "?" not in sbd and "?" not in md and r.get("trang_thai") != TRANG_THAI_LOI_ANH:
                key = (sbd, md)
                sbd_md_map.setdefault(key, []).append(i)

        for (sbd, md), idx_list in sbd_md_map.items():
            if len(idx_list) > 1:
                all_names = [self.danh_sach_ket_qua[i]["ten_anh_bai_lam"] for i in idx_list]
                for i in idx_list:
                    item = self.danh_sach_ket_qua[i]
                    item["nghi_trung_bai"] = True
                    item["file_trung"] = [f for f in all_names if f != item["ten_anh_bai_lam"]]
                    if not any("Nghi trùng bài" in w for w in item["warnings"]):
                        item["warnings"].append(f"Nghi trùng bài: cùng SBD {sbd} và Mã đề {md} với {', '.join(item['file_trung'])}")

        self.dang_cham = False
        if self.danh_sach_ket_qua and self.bai_hien_tai_idx == -1:
            self.bai_hien_tai_idx = 0
        return self.danh_sach_ket_qua

    def sua_tay_dap_an(self, bai_idx: int, cau_idx_0: int, dap_an_moi: str) -> dict[str, Any] | None:
        """
        Sửa tay 1 đáp án của câu hỏi (0-49) và tự động tính lại điểm.
        """
        if not (0 <= bai_idx < len(self.danh_sach_ket_qua)):
            return None
        res = self.danh_sach_ket_qua[bai_idx]
        if not res.get("chi_tiet_50_cau") or not (0 <= cau_idx_0 < 50):
            return None

        dap_an_moi = dap_an_moi.strip().upper()
        if dap_an_moi not in ("A", "B", "C", "D", "BLANK", ""):
            dap_an_moi = "BLANK" if not dap_an_moi else dap_an_moi

        # Cập nhật lựa chọn
        res["chi_tiet_50_cau"][cau_idx_0]["lua_chon"] = dap_an_moi
        res["chi_tiet_50_cau"][cau_idx_0]["sua_tay"] = True
        res["chi_tiet_50_cau"][cau_idx_0]["trang_thai"] = "HOP_LE" if dap_an_moi in ("A", "B", "C", "D") else "BLANK"

        # Tính lại điểm nếu có đáp án chuẩn
        ma_de = res.get("ma_de")
        if ma_de in self.tu_dien_dap_an:
            da_chuan = self.tu_dien_dap_an[ma_de]["answers"]
            so_dung, so_sai, so_blank, so_multi, so_amb, diem, chi_tiet = tinh_diem_50_cau(
                res["chi_tiet_50_cau"], da_chuan
            )
            res["so_dung"] = so_dung
            res["so_sai"] = so_sai
            res["so_blank"] = so_blank
            res["so_multi"] = so_multi
            res["so_ambiguous"] = so_amb
            res["diem"] = diem
            res["trang_thai"] = TRANG_THAI_DA_CHAM
            res["chi_tiet_50_cau"] = chi_tiet

        return res

    def sua_tay_ma_de(self, bai_idx: int, ma_de_moi: str) -> dict[str, Any] | None:
        """
        Sửa tay Mã đề của một bài làm và tự động chấm lại theo đáp án chuẩn của mã đề mới.
        """
        if not (0 <= bai_idx < len(self.danh_sach_ket_qua)):
            return None
        res = self.danh_sach_ket_qua[bai_idx]
        ma_de_moi = ma_de_moi.strip()
        res["ma_de"] = ma_de_moi
        res["sua_tay_made"] = True

        if ma_de_moi in self.tu_dien_dap_an:
            da_chuan = self.tu_dien_dap_an[ma_de_moi]["answers"]
            res["ma_de_khop"] = True
            res["ten_anh_dap_an"] = self.tu_dien_dap_an[ma_de_moi]["source_image"]
            res["trang_thai"] = TRANG_THAI_DA_CHAM
            res["ly_do"] = "Đã sửa tay mã đề và chấm thành công"
            so_dung, so_sai, so_blank, so_multi, so_amb, diem, chi_tiet = tinh_diem_50_cau(
                res["chi_tiet_50_cau"], da_chuan
            )
            res["so_dung"] = so_dung
            res["so_sai"] = so_sai
            res["so_blank"] = so_blank
            res["so_multi"] = so_multi
            res["so_ambiguous"] = so_amb
            res["diem"] = diem
            res["chi_tiet_50_cau"] = chi_tiet
        else:
            res["ma_de_khop"] = False
            res["trang_thai"] = TRANG_THAI_CHUA_CHAM
            res["ly_do"] = f"Mã đề '{ma_de_moi}' không có trong từ điển đáp án mẫu"
            res["diem"] = 0.0

        return res

    def sua_tay_sbd(self, bai_idx: int, sbd_moi: str) -> dict[str, Any] | None:
        """Sửa tay Số báo danh của bài làm."""
        if not (0 <= bai_idx < len(self.danh_sach_ket_qua)):
            return None
        res = self.danh_sach_ket_qua[bai_idx]
        res["sbd"] = sbd_moi.strip()
        res["sua_tay_sbd"] = True
        return res

    def xuat_ket_qua_excel(self, duong_dan: str) -> str:
        """Xuất file Excel tổng hợp kết quả."""
        return xuat_excel(self.danh_sach_ket_qua, self.tu_dien_dap_an, duong_dan)

    def xuat_ket_qua_sqlite(self, duong_dan: str) -> str:
        """Xuất kết quả ra cơ sở dữ liệu SQLite."""
        return xuat_sqlite(self.danh_sach_ket_qua, self.tu_dien_dap_an, duong_dan)


# =============================================================================
# HÀM TRỰC QUAN HÓA: VẼ ĐÁNH DẤU KẾT QUẢ TRÊN ẢNH PHIẾU ĐÃ NẮN
# =============================================================================

def ve_dau_tich(img: np.ndarray, x: int, y: int, size: int = 8, color=(0, 190, 0), thickness: int = 2) -> None:
    """Vẽ dấu tích chữ V (checkmark) biểu thị đáp án ĐÚNG."""
    p1 = (int(x - size * 0.5), int(y))
    p2 = (int(x - size * 0.1), int(y + size * 0.6))
    p3 = (int(x + size * 0.8), int(y - size * 0.7))
    cv2.line(img, p1, p2, color, thickness, cv2.LINE_AA)
    cv2.line(img, p2, p3, color, thickness, cv2.LINE_AA)


def ve_dau_cheo(img: np.ndarray, x: int, y: int, size: int = 7, color=(0, 0, 230), thickness: int = 2) -> None:
    """Vẽ dấu gạch chéo X (cross) biểu thị đáp án SAI."""
    r = int(size)
    cv2.line(img, (x - r, y - r), (x + r, y + r), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x - r, y + r), (x + r, y - r), color, thickness, cv2.LINE_AA)


def lay_toa_do_50_cau(config: dict | None = None) -> list[dict[str, tuple[int, int]]]:
    """Tính toán tọa độ tâm chuẩn của 50 câu hỏi từ cấu hình."""
    cfg = config if config is not None else nap_config()
    cfg_cau = cfg.get("roi_cau_hoi", {})
    hang_offsets = cfg_cau.get("hang_y_offsets", [16.6, 47.4, 78.4, 109.3, 140.2])
    nhan_opts = cfg_cau.get("dap_an_nhan", ["A", "B", "C", "D"])
    cot_1_5 = cfg_cau.get("cot_1_5_x_offsets", [90.0, 155.5, 219.7, 283.6])
    cot_6_10 = cfg_cau.get("cot_6_10_x_offsets", [88.5, 151.5, 220.0, 288.0])

    res = []
    for k_idx, khoi in enumerate(cfg_cau.get("khoi", [])):
        px = khoi["pixel_x"]
        py = khoi["pixel_y"]
        cot_offsets = cot_1_5 if k_idx < 5 else cot_6_10
        for r_idx in range(5):
            y_c = int(round(py + hang_offsets[r_idx]))
            m = {opt: (int(round(px + cot_offsets[c_idx])), y_c) for c_idx, opt in enumerate(nhan_opts)}
            res.append(m)
    return res


def ve_anh_da_cham(
    warped: np.ndarray,
    chi_tiet_50: list[dict[str, Any]],
    answers_chuan: list[str] | None = None,
    sbd: str = "????",
    ma_de: str = "???",
    diem: float | None = None,
    config: dict | None = None
) -> np.ndarray:
    """
    Vẽ ảnh phiếu đã chấm hoàn chỉnh có DẤU TÍCH ĐÚNG / SAI:
        - Dấu tích chữ V (xanh lá): Đánh dấu câu ĐÚNG trên ô tô và cuối dòng câu hỏi.
        - Dấu gạch chéo X (đỏ): Đánh dấu câu SAI trên ô chọn sai và cuối dòng câu hỏi.
        - Xanh lá khoanh ô đáp án đúng + dấu tích V: Chỉ rõ đáp án đúng nếu học sinh làm sai hoặc bỏ trống.
        - Dấu ? (vàng): Câu nghi ngờ mờ / tẩy chưa sạch (AMBIGUOUS).
        - Dấu ! (đỏ): Câu tô nhiều ô (MULTI).
        - Bảng điểm chi tiết ở header trên cùng: SBD, Mã đề, Số câu đúng, Điểm số.
    """
    vis = warped.copy()
    if len(vis.shape) == 2:
        vis = cv2.cvtColor(vis, cv2.COLOR_GRAY2BGR)

    cfg = config if config is not None else nap_config()
    toa_do_chuan = lay_toa_do_50_cau(cfg)
    bk = cfg.get("roi_cau_hoi", {}).get("ban_kinh_o_pixel", 8)

    so_cau_dung = 0

    for idx in range(min(50, len(chi_tiet_50))):
        item = chi_tiet_50[idx]
        cau_so = item.get("cau", idx + 1)
        student_opt = item.get("lua_chon", "")
        chuan_opt = answers_chuan[idx] if (answers_chuan and idx < len(answers_chuan)) else None
        kq = item.get("ket_qua")

        # Lấy tọa độ tâm các ô của câu này
        tam_map = item.get("toa_do_tam")
        if not tam_map and idx < len(toa_do_chuan):
            tam_map = toa_do_chuan[idx]

        if not tam_map:
            continue

        x_d, y_cau = tam_map.get("D", (880, 600))
        # Vị trí đánh dấu cuối dòng (sau ô D)
        x_badge = x_d + 24

        # 1. Trường hợp ĐÚNG
        if (kq == "DUNG") or (chuan_opt and student_opt == chuan_opt):
            so_cau_dung += 1
            if student_opt in tam_map:
                p_opt = tam_map[student_opt]
                cv2.circle(vis, p_opt, bk + 4, (0, 190, 0), 2, cv2.LINE_AA)
                ve_dau_tich(vis, p_opt[0], p_opt[1], size=6, color=(0, 190, 0), thickness=2)
            # Dấu tích xanh cuối dòng câu hỏi
            ve_dau_tich(vis, x_badge, y_cau, size=9, color=(0, 190, 0), thickness=2)

        # 2. Trường hợp SAI (chọn A/B/C/D nhưng sai)
        elif (kq == "SAI") or (chuan_opt and student_opt in ("A", "B", "C", "D") and student_opt != chuan_opt):
            # Ô chọn sai: khoanh đỏ + gạch chéo X đỏ
            if student_opt in tam_map:
                p_opt = tam_map[student_opt]
                cv2.circle(vis, p_opt, bk + 4, (0, 0, 230), 2, cv2.LINE_AA)
                ve_dau_cheo(vis, p_opt[0], p_opt[1], size=bk + 1, color=(0, 0, 230), thickness=2)

            # Ô đáp án đúng: khoanh xanh lá + dấu tích V xanh nhỏ
            if chuan_opt in tam_map:
                p_chuan = tam_map[chuan_opt]
                cv2.circle(vis, p_chuan, bk + 4, (0, 180, 0), 2, cv2.LINE_AA)
                ve_dau_tich(vis, p_chuan[0], p_chuan[1], size=6, color=(0, 180, 0), thickness=2)

            # Dấu chéo đỏ cuối dòng + đáp án đúng
            ve_dau_cheo(vis, x_badge - 2, y_cau, size=7, color=(0, 0, 230), thickness=2)
            cv2.putText(vis, f">{chuan_opt}", (x_badge + 8, y_cau + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 160, 0), 1, cv2.LINE_AA)

        # 3. Trường hợp BỎ TRỐNG (BLANK)
        elif (kq == "BLANK") or (student_opt == "BLANK"):
            if chuan_opt in tam_map:
                p_chuan = tam_map[chuan_opt]
                cv2.circle(vis, p_chuan, bk + 4, (0, 180, 0), 2, cv2.LINE_AA)
                ve_dau_tich(vis, p_chuan[0], p_chuan[1], size=6, color=(0, 180, 0), thickness=2)

            cv2.line(vis, (x_badge - 5, y_cau), (x_badge + 3, y_cau), (120, 120, 120), 2, cv2.LINE_AA)
            if chuan_opt:
                cv2.putText(vis, f">{chuan_opt}", (x_badge + 8, y_cau + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 160, 0), 1, cv2.LINE_AA)

        # 4. Trường hợp NGHI NGỜ (AMBIGUOUS)
        elif item.get("trang_thai") == "AMBIGUOUS" or kq == "AMBIGUOUS":
            for opt, center in tam_map.items():
                if item.get("fill_ratios", {}).get(opt, 0) >= 0.20:
                    cv2.circle(vis, center, bk + 4, (0, 215, 255), 2, cv2.LINE_AA)
            cv2.putText(vis, "?", (x_badge, y_cau + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 190, 240), 2, cv2.LINE_AA)

        # 5. Trường hợp TÔ NHIỀU (MULTI)
        elif item.get("trang_thai") == "MULTI" or kq == "MULTI":
            for opt, center in tam_map.items():
                if item.get("fill_ratios", {}).get(opt, 0) >= 0.35:
                    cv2.circle(vis, center, bk + 4, (0, 0, 255), 2, cv2.LINE_AA)
            cv2.putText(vis, "!", (x_badge, y_cau + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 240), 2, cv2.LINE_AA)

    # Header trên cùng
    diem_str = f"{diem:.2f} ĐIỂM" if diem is not None else "-- ĐIỂM"
    color_diem = (0, 150, 0) if (diem is not None and diem >= 5.0) else (0, 0, 200)

    cv2.rectangle(vis, (40, 20), (1015, 68), (255, 255, 255), -1)
    cv2.rectangle(vis, (40, 20), (1015, 68), (200, 200, 200), 1)
    cv2.putText(
        vis,
        f"SBD: {sbd}   |   MA DE: {ma_de}   |   DUNG: {so_cau_dung:02d}/50",
        (55, 52),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.72,
        (40, 40, 40),
        2,
        cv2.LINE_AA
    )
    cv2.putText(
        vis,
        f"KET QUA: {diem_str}",
        (720, 52),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        color_diem,
        2,
        cv2.LINE_AA
    )

    return vis


# =============================================================================
# CÁC WIDGET BỔ TRỢ: CUỘN CHUỘT & PHÓNG TO ẢNH (IMAGE ZOOM VIEWER)
# =============================================================================

def gan_cuon_chuot(widget: tk.Widget) -> None:
    """Gắn sự kiện lăn chuột cho widget (Treeview, Canvas...)."""
    def _on_wheel(event):
        try:
            widget.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass
        return "break"

    def _on_enter(event):
        widget.bind_all("<MouseWheel>", _on_wheel)

    def _on_leave(event):
        widget.unbind_all("<MouseWheel>")

    widget.bind("<Enter>", _on_enter, add="+")
    widget.bind("<Leave>", _on_leave, add="+")
    widget.bind("<MouseWheel>", _on_wheel, add="+")
    widget.bind("<Button-4>", lambda e: widget.yview_scroll(-1, "units"), add="+")
    widget.bind("<Button-5>", lambda e: widget.yview_scroll(1, "units"), add="+")


class ScrollableFrame(ttk.Frame):
    """Khung giao diện có thanh cuộn và hỗ trợ cuộn chuột mượt mà."""

    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_content = ttk.Frame(self.canvas)

        self.scrollable_content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self._window_id = self.canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Bắt sự kiện cuộn chuột khi con trỏ di vào khung
        self.bind("<Enter>", self._on_enter, add="+")
        self.bind("<Leave>", self._on_leave, add="+")
        self.canvas.bind("<Enter>", self._on_enter, add="+")
        self.canvas.bind("<Leave>", self._on_leave, add="+")
        self.scrollable_content.bind("<Enter>", self._on_enter, add="+")
        self.scrollable_content.bind("<Leave>", self._on_leave, add="+")

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self._window_id, width=event.width)

    def _on_enter(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_leave(self, event):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        try:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    def cap_nhat_cuon(self):
        """Cập nhật lại vùng cuộn và gắn sự kiện lăn chuột cho tất cả widget con."""
        self.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._gan_de_quy(self.scrollable_content)

    def _gan_de_quy(self, widget):
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"), add="+")
        widget.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"), add="+")
        for child in widget.winfo_children():
            self._gan_de_quy(child)


class CuaSoPhongToAnh(tk.Toplevel):
    """
    Cửa sổ phóng to xem chi tiết ảnh độ phân giải cao:
        - Hỗ trợ cuộn chuột lăn mượt mà (dọc & ngang).
        - Phóng to (Zoom In), Thu nhỏ (Zoom Out), Vừa khung hình (Fit), Kích thước thật (100%).
        - Kéo thả chuột để di chuyển ảnh (Drag & Pan).
        - Lưu ảnh ra máy tính.
    """

    def __init__(self, parent: tk.Widget, rgb_image: np.ndarray, tieu_de: str = "Xem ảnh chi tiết"):
        super().__init__(parent)
        self.title(tieu_de)
        self.geometry("1100x800")
        self.minsize(700, 500)

        self.rgb_image = rgb_image
        self.pil_image = Image.fromarray(rgb_image)
        self.orig_w, self.orig_h = self.pil_image.size

        self.zoom_scale = 1.0
        self._photo_cache = None

        self._tao_thanh_cong_cu(tieu_de)
        self._tao_canvas_anh()

        # Tự động tính tỉ lệ vừa khung hình ban đầu
        self.after(60, self._fit_to_window)

    def _tao_thanh_cong_cu(self, tieu_de: str):
        tb = ttk.Frame(self, padding=6)
        tb.pack(side=tk.TOP, fill=tk.X)

        # Tiêu đề bên trái
        ttk.Label(tb, text=tieu_de, font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT, padx=6)

        # Nút đóng
        ttk.Button(tb, text="Đóng", command=self.destroy).pack(side=tk.RIGHT, padx=4)

        # Nút lưu ảnh
        ttk.Button(tb, text="Lưu ảnh...", command=self._luu_anh).pack(side=tk.RIGHT, padx=4)

        # Phân cách
        ttk.Separator(tb, orient="vertical").pack(side=tk.RIGHT, fill=tk.Y, padx=6)

        # Các nút zoom
        ttk.Button(tb, text="100%", width=6, command=lambda: self._set_zoom(1.0)).pack(side=tk.RIGHT, padx=2)
        ttk.Button(tb, text="Vừa khung", command=self._fit_to_window).pack(side=tk.RIGHT, padx=2)
        ttk.Button(tb, text="Thu nhỏ", command=self._zoom_out).pack(side=tk.RIGHT, padx=2)
        self.lbl_zoom = ttk.Label(tb, text="100%", font=("Segoe UI", 9, "bold"), width=6, anchor="center")
        self.lbl_zoom.pack(side=tk.RIGHT, padx=2)
        ttk.Button(tb, text="Phóng to", command=self._zoom_in).pack(side=tk.RIGHT, padx=2)

    def _tao_canvas_anh(self):
        # Thanh hướng dẫn ở chân cửa sổ
        sb_hint = ttk.Frame(self, padding=(8, 3), relief=tk.SUNKEN)
        sb_hint.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(
            sb_hint,
            text="Lăn chuột: Cuộn dọc | Shift + Lăn: Cuộn ngang | Ctrl + Lăn: Phóng to / Thu nhỏ | Kéo chuột trái: Di chuyển tự do",
            font=("Segoe UI", 9),
            foreground="#444"
        ).pack(side=tk.LEFT)

        frame_canvas = ttk.Frame(self)
        frame_canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(frame_canvas, bg="#1e1e1e", highlightthickness=0)
        self.sb_y = ttk.Scrollbar(frame_canvas, orient="vertical", command=self.canvas.yview)
        self.sb_x = ttk.Scrollbar(frame_canvas, orient="horizontal", command=self.canvas.xview)

        self.canvas.configure(xscrollcommand=self.sb_x.set, yscrollcommand=self.sb_y.set)

        self.sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.sb_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bind chuột cuộn và kéo thả
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)
        self.canvas.config(cursor="fleur")

    def _on_drag_start(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def _on_drag_motion(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_mousewheel(self, event):
        # Nếu giữ Ctrl -> Zoom in/out
        if event.state & 0x0004:
            if event.delta > 0:
                self._zoom_in()
            else:
                self._zoom_out()
        elif event.state & 0x0001:  # Shift -> cuộn ngang
            self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        else:  # Cuộn dọc
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _set_zoom(self, new_scale: float):
        self.zoom_scale = max(0.15, min(3.5, new_scale))
        self.lbl_zoom.configure(text=f"{int(self.zoom_scale * 100)}%")
        self._render_image()

    def _zoom_in(self):
        self._set_zoom(self.zoom_scale * 1.25)

    def _zoom_out(self):
        self._set_zoom(self.zoom_scale / 1.25)

    def _fit_to_window(self):
        self.update_idletasks()
        c_w = self.canvas.winfo_width()
        c_h = self.canvas.winfo_height()
        if c_w <= 1 or c_h <= 1:
            c_w = 1000
            c_h = 700
        scale_w = (c_w - 20) / float(self.orig_w)
        scale_h = (c_h - 20) / float(self.orig_h)
        fit_scale = min(scale_w, scale_h)
        self._set_zoom(fit_scale)

    def _render_image(self):
        cur_w = max(10, int(self.orig_w * self.zoom_scale))
        cur_h = max(10, int(self.orig_h * self.zoom_scale))
        resized_pil = self.pil_image.resize((cur_w, cur_h), Image.Resampling.LANCZOS)
        self._photo_cache = ImageTk.PhotoImage(resized_pil)

        self.canvas.delete("all")
        c_w = max(self.canvas.winfo_width(), cur_w)
        c_h = max(self.canvas.winfo_height(), cur_h)
        x_pos = max(0, (c_w - cur_w) // 2)
        y_pos = max(0, (c_h - cur_h) // 2)

        self.canvas.create_image(x_pos, y_pos, anchor="nw", image=self._photo_cache)
        self.canvas.configure(scrollregion=(0, 0, max(c_w, cur_w), max(c_h, cur_h)))

    def _luu_anh(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg;*.jpeg"), ("All Files", "*.*")]
        )
        if path:
            try:
                self.pil_image.save(path)
                messagebox.showinfo("Thành công", f"Đã lưu ảnh ra:\n{path}")
            except Exception as e:
                messagebox.showerror("Lỗi lưu ảnh", f"Không thể lưu ảnh: {e}")


# =============================================================================
# GIAO DIỆN NGƯỜI DÙNG TKINTER (VIEW)
# =============================================================================

class OMRMainWindow:
    """Cửa sổ giao diện chính của phần mềm OMR."""

    def __init__(self, root: tk.Tk, controller: OMRController | None = None):
        self.root = root
        self.root.title("Hệ thống chấm thi trắc nghiệm 50 câu")
        self.root.geometry("1366x768")
        self.root.minsize(1024, 600)

        # Controller
        self.controller = controller if controller is not None else OMRController()

        # Biến trạng thái hiển thị
        self.var_trang_thai = tk.StringVar(value="Sẵn sàng. Hãy bắt đầu bằng Bước 1: Nạp đáp án mẫu.")
        self.var_tien_do = tk.DoubleVar(value=0.0)
        self.var_so_luong_bai = tk.StringVar(value="Chưa có bài làm nào.")
        self.var_override_ma_de = tk.StringVar(value="567")
        self.var_thong_tin_bai = tk.StringVar(value="")

        # Cache ảnh hiển thị tránh bị GC thu hồi
        self._photo_goc = None
        self._photo_cham = None

        # Dữ liệu ảnh độ phân giải cao phục vụ phóng to (Zoom)
        self._anh_goc_full_rgb = None
        self._anh_cham_full_rgb = None
        self._ten_anh_hien_tai = ""

        self._cai_dat_phong_cach()
        self._tao_giao_dien()
        self._kiem_tra_webcam_ban_dau()

    def _cai_dat_phong_cach(self) -> None:
        """Thiết lập font chữ và style hiện đại cho ttk."""
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.font_chuan = ("Segoe UI", 10)
        self.font_dam = ("Segoe UI", 10, "bold")
        self.font_tieu_de = ("Segoe UI", 11, "bold")

        self.style.configure(".", font=self.font_chuan)
        self.style.configure("Treeview.Heading", font=self.font_dam)
        self.style.configure("TButton", padding=5, font=self.font_chuan)
        self.style.configure("Primary.TButton", font=self.font_dam, foreground="#ffffff", background="#2563eb")
        self.style.configure("Success.TButton", font=self.font_dam, foreground="#ffffff", background="#059669")

    def _tao_giao_dien(self) -> None:
        """Xây dựng bố cục 3 bước theo nghiệp vụ của giáo viên."""
        # Khung chính 2 cột lớn (Trái: Bảng điều khiển 3 bước; Phải: Kết quả & Ảnh xem trước)
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        # Cột trái: Điều khiển trong khung cuộn mượt mà
        self.scroll_trai = ScrollableFrame(paned, width=440)
        paned.add(self.scroll_trai, weight=0)
        frame_trai = self.scroll_trai.scrollable_content

        # Cột phải: Xem ảnh & Chi tiết bảng điểm (Co giãn)
        frame_phai = ttk.Frame(paned)
        paned.add(frame_phai, weight=1)

        self._tao_buoc_1_dap_an_mau(frame_trai)
        self._tao_buoc_2_bai_lam(frame_trai)
        self._tao_buoc_3_cham_bai(frame_trai)

        # Cập nhật thanh cuộn và gắn sự kiện lăn chuột cho toàn bộ cột trái
        self.scroll_trai.cap_nhat_cuon()

        self._tao_khung_xem_anh_va_ket_qua(frame_phai)
        self._tao_thanh_trang_thai()

    # -------------------------------------------------------------------------
    # BƯỚC 1: ĐÁP ÁN MẪU
    # -------------------------------------------------------------------------
    def _tao_buoc_1_dap_an_mau(self, parent: ttk.Frame) -> None:
        lbl_frame = ttk.LabelFrame(parent, text=" BƯỚC 1: ĐÁP ÁN MẪU CHUẨN ", padding=8)
        lbl_frame.pack(fill=tk.X, padx=4, pady=4)

        # Hàng nút chọn
        btn_box = ttk.Frame(lbl_frame)
        btn_box.pack(fill=tk.X, pady=2)

        btn_file = ttk.Button(btn_box, text="Chọn file ảnh mẫu", command=self._on_chon_file_dap_an)
        btn_file.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        btn_dir = ttk.Button(btn_box, text="Chọn thư mục mẫu", command=self._on_chon_thu_muc_dap_an)
        btn_dir.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        # Tùy chọn gán mã đề dự phòng nếu ảnh mẫu để trống mã đề
        row_md = ttk.Frame(lbl_frame)
        row_md.pack(fill=tk.X, pady=4)
        ttk.Label(row_md, text="Mã đề ghi đè (nếu mẫu để trống):", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        entry_md = ttk.Entry(row_md, textvariable=self.var_override_ma_de, width=6)
        entry_md.pack(side=tk.LEFT, padx=4)

        # Bảng hiển thị các mã đề đã nạp
        cols = ("ma_de", "so_cau", "nguon")
        self.tree_dap_an = ttk.Treeview(lbl_frame, columns=cols, show="headings", height=3)
        self.tree_dap_an.heading("ma_de", text="Mã đề")
        self.tree_dap_an.heading("so_cau", text="Số câu")
        self.tree_dap_an.heading("nguon", text="File nguồn")
        self.tree_dap_an.column("ma_de", width=65, anchor="center")
        self.tree_dap_an.column("so_cau", width=65, anchor="center")
        self.tree_dap_an.column("nguon", width=220, anchor="w")
        self.tree_dap_an.pack(fill=tk.X, pady=4)
        self.tree_dap_an.bind("<<TreeviewSelect>>", self._on_chon_ma_de_dap_an)
        self.tree_dap_an.bind("<Double-1>", lambda e: self._phong_to_anh_mau())
        gan_cuon_chuot(self.tree_dap_an)

        # Hàng nút: Xem ảnh mẫu & Sửa tay đáp án chuẩn
        row_btn_da = ttk.Frame(lbl_frame)
        row_btn_da.pack(fill=tk.X, pady=2)

        btn_xem_mau = ttk.Button(row_btn_da, text="Phóng to xem ảnh mẫu", command=self._phong_to_anh_mau)
        btn_xem_mau.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        btn_sua_da = ttk.Button(row_btn_da, text="Sửa đáp án chuẩn", command=self._on_sua_dap_an_chuan)
        btn_sua_da.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

    # -------------------------------------------------------------------------
    # BƯỚC 2: BÀI LÀM HỌC SINH
    # -------------------------------------------------------------------------
    def _tao_buoc_2_bai_lam(self, parent: ttk.Frame) -> None:
        lbl_frame = ttk.LabelFrame(parent, text=" BƯỚC 2: BÀI LÀM CỦA HỌC SINH ", padding=8)
        lbl_frame.pack(fill=tk.X, padx=4, pady=4)

        btn_box = ttk.Frame(lbl_frame)
        btn_box.pack(fill=tk.X, pady=2)

        btn_file = ttk.Button(btn_box, text="Chọn 1 ảnh", command=self._on_chon_file_bai_lam)
        btn_file.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        btn_dir = ttk.Button(btn_box, text="Chọn thư mục", command=self._on_chon_thu_muc_bai_lam)
        btn_dir.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        self.btn_webcam = ttk.Button(btn_box, text="Chụp từ Camera / Điện thoại", command=self._on_chup_webcam)
        self.btn_webcam.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        # Khung cấu hình Camera IP (điện thoại kết nối qua DroidCam/IP Webcam)
        frame_cam_ip = ttk.Frame(lbl_frame)
        frame_cam_ip.pack(fill=tk.X, pady=2)
        ttk.Label(frame_cam_ip, text="Camera IP (URL):", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.var_camera_ip = tk.StringVar(value="")
        self.entry_cam_ip = ttk.Entry(frame_cam_ip, textvariable=self.var_camera_ip, width=30)
        self.entry_cam_ip.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)
        ttk.Label(
            frame_cam_ip,
            text="Ví dụ: http://192.168.1.5:4747/video",
            font=("Segoe UI", 8),
            foreground="#888"
        ).pack(side=tk.LEFT, padx=2)

        # Thông tin số lượng bài đã chọn
        lbl_info = ttk.Label(lbl_frame, textvariable=self.var_so_luong_bai, foreground="#1e3a8a", font=self.font_dam)
        lbl_info.pack(anchor="w", pady=4)

        btn_clear = ttk.Button(lbl_frame, text="Xóa danh sách bài làm", command=self._on_xoa_danh_sach)
        btn_clear.pack(anchor="e", pady=2)

    # -------------------------------------------------------------------------
    # BƯỚC 3: CHẤM BÀI & XUẤT KẾT QUẢ
    # -------------------------------------------------------------------------
    def _tao_buoc_3_cham_bai(self, parent: ttk.Frame) -> None:
        lbl_frame = ttk.LabelFrame(parent, text=" BƯỚC 3: CHẤM & XUẤT DỮ LIỆU ", padding=8)
        lbl_frame.pack(fill=tk.X, padx=4, pady=4)

        # Nút chấm chính
        self.btn_cham = ttk.Button(
            lbl_frame,
            text="BẮT ĐẦU CHẤM BÀI",
            style="Success.TButton",
            command=self._on_bat_dau_cham
        )
        self.btn_cham.pack(fill=tk.X, pady=4)

        # Thanh tiến trình
        self.prog_bar = ttk.Progressbar(lbl_frame, variable=self.var_tien_do, maximum=100.0)
        self.prog_bar.pack(fill=tk.X, pady=4)

        # Nút xuất Excel & SQLite
        row_exp = ttk.Frame(lbl_frame)
        row_exp.pack(fill=tk.X, pady=4)

        btn_excel = ttk.Button(row_exp, text="Xuất Excel...", command=self._on_xuat_excel)
        btn_excel.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        btn_sqlite = ttk.Button(row_exp, text="Lưu SQLite...", command=self._on_xuat_sqlite)
        btn_sqlite.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

    # -------------------------------------------------------------------------
    # CỘT PHẢI: BẢNG KẾT QUẢ, XEM ẢNH & CHI TIẾT 50 CÂU
    # -------------------------------------------------------------------------
    def _tao_khung_xem_anh_va_ket_qua(self, parent: ttk.Frame) -> None:
        # Chia cột phải thành 2 nửa: Nửa trên là bảng điểm + chi tiết; Nửa dưới là ảnh xem trước
        paned_phai = ttk.PanedWindow(parent, orient=tk.VERTICAL)
        paned_phai.pack(fill=tk.BOTH, expand=True)

        # Nửa trên: Bảng điểm danh sách & Panel chi tiết 50 câu
        frame_top = ttk.Frame(paned_phai)
        paned_phai.add(frame_top, weight=1)

        paned_top = ttk.PanedWindow(frame_top, orient=tk.HORIZONTAL)
        paned_top.pack(fill=tk.BOTH, expand=True)

        # Bảng điểm tổng hợp (Treeview)
        frame_bang = ttk.LabelFrame(paned_top, text=" DANH SÁCH BÀI ĐÃ CHẤM ", padding=4)
        paned_top.add(frame_bang, weight=3)

        cols = ("stt", "file", "sbd", "ma_de", "dung", "sai", "diem", "trang_thai")
        self.tree_ket_qua = ttk.Treeview(frame_bang, columns=cols, show="headings")
        self.tree_ket_qua.heading("stt", text="STT")
        self.tree_ket_qua.heading("file", text="Tên file ảnh")
        self.tree_ket_qua.heading("sbd", text="SBD")
        self.tree_ket_qua.heading("ma_de", text="Mã đề")
        self.tree_ket_qua.heading("dung", text="Đúng")
        self.tree_ket_qua.heading("sai", text="Sai")
        self.tree_ket_qua.heading("diem", text="Điểm")
        self.tree_ket_qua.heading("trang_thai", text="Trạng thái")

        self.tree_ket_qua.column("stt", width=40, anchor="center")
        self.tree_ket_qua.column("file", width=140, anchor="w")
        self.tree_ket_qua.column("sbd", width=60, anchor="center")
        self.tree_ket_qua.column("ma_de", width=60, anchor="center")
        self.tree_ket_qua.column("dung", width=50, anchor="center")
        self.tree_ket_qua.column("sai", width=50, anchor="center")
        self.tree_ket_qua.column("diem", width=60, anchor="center")
        self.tree_ket_qua.column("trang_thai", width=90, anchor="center")

        sb_y = ttk.Scrollbar(frame_bang, orient=tk.VERTICAL, command=self.tree_ket_qua.yview)
        self.tree_ket_qua.configure(yscrollcommand=sb_y.set)
        self.tree_ket_qua.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_ket_qua.bind("<<TreeviewSelect>>", self._on_chon_dong_ket_qua)
        gan_cuon_chuot(self.tree_ket_qua)

        # Panel chi tiết 50 câu & sửa tay
        frame_chi_tiet = ttk.LabelFrame(paned_top, text=" CHI TIẾT 50 CÂU & SỬA TAY ", padding=4)
        paned_top.add(frame_chi_tiet, weight=2)

        # Thanh công cụ sửa tay SBD / Mã đề
        tool_edit = ttk.Frame(frame_chi_tiet)
        tool_edit.pack(fill=tk.X, pady=2)

        ttk.Label(tool_edit, text="SBD:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.entry_sbd = ttk.Entry(tool_edit, width=6)
        self.entry_sbd.pack(side=tk.LEFT, padx=2)

        ttk.Label(tool_edit, text="Mã đề:", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(4, 0))
        self.entry_made = ttk.Entry(tool_edit, width=5)
        self.entry_made.pack(side=tk.LEFT, padx=2)

        btn_apply_id = ttk.Button(tool_edit, text="Lưu SBD/Mã đề", command=self._on_luu_sbd_made)
        btn_apply_id.pack(side=tk.LEFT, padx=4)

        # Bảng 50 câu (Treeview)
        q_cols = ("cau", "chon", "chuan", "kq")
        self.tree_cau = ttk.Treeview(frame_chi_tiet, columns=q_cols, show="headings", height=8)
        self.tree_cau.heading("cau", text="Câu")
        self.tree_cau.heading("chon", text="Đã tô")
        self.tree_cau.heading("chuan", text="Đáp án")
        self.tree_cau.heading("kq", text="Kết quả")
        self.tree_cau.column("cau", width=45, anchor="center")
        self.tree_cau.column("chon", width=60, anchor="center")
        self.tree_cau.column("chuan", width=60, anchor="center")
        self.tree_cau.column("kq", width=70, anchor="center")

        sb_q = ttk.Scrollbar(frame_chi_tiet, orient=tk.VERTICAL, command=self.tree_cau.yview)
        self.tree_cau.configure(yscrollcommand=sb_q.set)
        self.tree_cau.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_q.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_cau.bind("<Double-1>", self._on_double_click_cau)
        gan_cuon_chuot(self.tree_cau)

        # Nửa dưới: Khung xem ảnh gốc vs ảnh đã chấm (Có click phóng to)
        frame_anh = ttk.LabelFrame(paned_phai, text=" TRỰC QUAN HÓA: ẢNH GỐC vs ẢNH ĐÃ CHẤM (CLICK VÀO ẢNH ĐỂ PHÓNG TO) ", padding=4)
        paned_phai.add(frame_anh, weight=1)

        paned_anh = ttk.PanedWindow(frame_anh, orient=tk.HORIZONTAL)
        paned_anh.pack(fill=tk.BOTH, expand=True)

        # Khung trái: Ảnh gốc bài làm
        box_goc = ttk.Frame(paned_anh)
        paned_anh.add(box_goc, weight=1)

        hdr_goc = ttk.Frame(box_goc)
        hdr_goc.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(hdr_goc, text="ẢNH BÀI LÀM GỐC", font=self.font_dam).pack(side=tk.LEFT, padx=4)
        ttk.Button(hdr_goc, text="Phóng to ảnh gốc", command=self._phong_to_anh_goc).pack(side=tk.RIGHT, padx=2)

        self.lbl_anh_goc = ttk.Label(
            box_goc,
            text="Chưa có ảnh gốc\n(Nhấp chuột hoặc bấm Phóng to để xem chi tiết)",
            anchor="center",
            justify="center",
            background="#262626",
            foreground="#d4d4d4",
            cursor="hand2"
        )
        self.lbl_anh_goc.pack(fill=tk.BOTH, expand=True)
        self.lbl_anh_goc.bind("<Button-1>", lambda e: self._phong_to_anh_goc())

        # Khung phải: Ảnh đã chấm có dấu tích đúng/sai
        box_cham = ttk.Frame(paned_anh)
        paned_anh.add(box_cham, weight=1)

        hdr_cham = ttk.Frame(box_cham)
        hdr_cham.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(hdr_cham, text="ẢNH ĐÃ CHẤM (TÍCH ĐÚNG / SAI)", font=self.font_dam).pack(side=tk.LEFT, padx=4)
        ttk.Button(hdr_cham, text="Phóng to ảnh đã chấm", command=self._phong_to_anh_cham).pack(side=tk.RIGHT, padx=2)

        self.lbl_anh_cham = ttk.Label(
            box_cham,
            text="Chưa có ảnh đã chấm\n(Nhấp chuột hoặc bấm Phóng to để xem chi tiết)",
            anchor="center",
            justify="center",
            background="#262626",
            foreground="#d4d4d4",
            cursor="hand2"
        )
        self.lbl_anh_cham.pack(fill=tk.BOTH, expand=True)
        self.lbl_anh_cham.bind("<Button-1>", lambda e: self._phong_to_anh_cham())

    def _tao_thanh_trang_thai(self) -> None:
        """Tạo thanh trạng thái dưới chân cửa sổ."""
        status_frame = ttk.Frame(self.root, relief=tk.SUNKEN, padding=(6, 2))
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        lbl_status = ttk.Label(status_frame, textvariable=self.var_trang_thai, font=("Segoe UI", 9))
        lbl_status.pack(side=tk.LEFT)

    def _kiem_tra_webcam_ban_dau(self) -> None:
        """Kiểm tra camera ban đầu trên luồng nền để khởi động app nhanh chóng."""
        def _check():
            try:
                co_cam_usb = kiem_tra_camera()
                if not co_cam_usb:
                    self.root.after(0, lambda: self.var_trang_thai.set("Chưa cắm camera USB. Bạn có thể kết nối Camera IP điện thoại để chụp."))
            except Exception:
                pass
        threading.Thread(target=_check, daemon=True).start()

    # -------------------------------------------------------------------------
    # CÁC SỰ KIỆN NẠP DỮ LIỆU
    # -------------------------------------------------------------------------
    def _on_chon_file_dap_an(self) -> None:
        path = filedialog.askopenfilename(
            title="Chọn ảnh phiếu đáp án mẫu",
            filetypes=[("File ảnh", "*.png *.jpg *.jpeg *.bmp"), ("Tất cả", "*.*")]
        )
        if not path:
            return
        override = self.var_override_ma_de.get().strip()
        ok, msg = self.controller.nap_dap_an_tu_file(path, override_ma_de=override)
        if ok:
            self._cap_nhat_bang_dap_an()
            self.var_trang_thai.set(msg)
            messagebox.showinfo("Thành công", msg)
        else:
            messagebox.showerror("Lỗi", msg)

    def _on_chon_thu_muc_dap_an(self) -> None:
        path = filedialog.askdirectory(title="Chọn thư mục chứa ảnh đáp án mẫu")
        if not path:
            return
        override = self.var_override_ma_de.get().strip() or None
        ok, msg = self.controller.nap_dap_an_tu_thu_muc(path, override_ma_de=override)
        if ok:
            self._cap_nhat_bang_dap_an()
            self.var_trang_thai.set(msg)
            messagebox.showinfo("Thành công", msg)
        else:
            messagebox.showerror("Lỗi", msg)

    def _cap_nhat_bang_dap_an(self) -> None:
        """Làm mới danh sách mã đề trong bảng đáp án."""
        self.tree_dap_an.delete(*self.tree_dap_an.get_children())
        for md, info in self.controller.tu_dien_dap_an.items():
            self.tree_dap_an.insert("", tk.END, values=(md, f"{len(info['answers'])} câu", info["source_image"]))

    def _on_chon_ma_de_dap_an(self, event=None) -> None:
        pass

    def _on_sua_dap_an_chuan(self) -> None:
        """Mở cửa sổ con cho phép giáo viên xem và sửa trực tiếp 50 đáp án chuẩn."""
        if not self.controller.tu_dien_dap_an:
            messagebox.showwarning("Cảnh báo", "Chưa có đáp án mẫu nào được nạp.")
            return

        sel = self.tree_dap_an.selection()
        if not sel:
            ma_de = list(self.controller.tu_dien_dap_an.keys())[0]
        else:
            ma_de = str(self.tree_dap_an.item(sel[0], "values")[0])

        dlg = tk.Toplevel(self.root)
        dlg.title(f"Xác nhận & Sửa đáp án chuẩn – Mã đề {ma_de}")
        dlg.geometry("520x600")
        dlg.transient(self.root)
        dlg.grab_set()

        ttk.Label(dlg, text=f"BẢNG 50 ĐÁP ÁN CHUẨN (MÃ ĐỀ: {ma_de})", font=self.font_dam).pack(pady=8)
        ttk.Label(dlg, text="Bạn có thể sửa lại nếu phần mềm nhận diện sai:").pack()

        frame_scroll = ttk.Frame(dlg)
        frame_scroll.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        canvas = tk.Canvas(frame_scroll, borderwidth=0)
        sb = ttk.Scrollbar(frame_scroll, orient=tk.VERTICAL, command=canvas.yview)
        scroll_content = ttk.Frame(canvas)
        scroll_content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_content, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        curr_answers = list(self.controller.tu_dien_dap_an[ma_de]["answers"])
        var_list = []

        # Hiển thị 50 câu chia thành 2 cột (1-25 bên trái, 26-50 bên phải)
        col_left = ttk.Frame(scroll_content)
        col_left.pack(side=tk.LEFT, padx=15, fill=tk.Y)
        col_right = ttk.Frame(scroll_content)
        col_right.pack(side=tk.LEFT, padx=15, fill=tk.Y)

        for i in range(50):
            p = col_left if i < 25 else col_right
            row = ttk.Frame(p)
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=f"Câu {i+1:02d}:", width=8).pack(side=tk.LEFT)
            v = tk.StringVar(value=curr_answers[i] if i < len(curr_answers) else "A")
            cb = ttk.Combobox(row, textvariable=v, values=["A", "B", "C", "D"], width=4, state="readonly")
            cb.pack(side=tk.LEFT)
            var_list.append(v)

        def _save_close():
            new_ans = [v.get() for v in var_list]
            self.controller.cap_nhat_dap_an_chuan(ma_de, new_ans)
            messagebox.showinfo("Thành công", f"Đã cập nhật 50 đáp án chuẩn cho mã đề {ma_de}.")
            dlg.destroy()

        btn_box = ttk.Frame(dlg)
        btn_box.pack(fill=tk.X, pady=10, padx=12)
        ttk.Button(btn_box, text="Lưu và Xác nhận", style="Success.TButton", command=_save_close).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_box, text="Đóng", command=dlg.destroy).pack(side=tk.RIGHT)

    def _on_chon_file_bai_lam(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Chọn ảnh bài làm của học sinh",
            filetypes=[("File ảnh", "*.png *.jpg *.jpeg *.bmp"), ("Tất cả", "*.*")]
        )
        if not paths:
            return
        added = 0
        for p in paths:
            ok, _ = self.controller.them_anh_bai_lam(p)
            if ok:
                added += 1
        self.var_so_luong_bai.set(f"Đã chọn {len(self.controller.danh_sach_bai_lam)} ảnh bài làm.")
        self.var_trang_thai.set(f"Đã thêm {added} ảnh bài làm vào danh sách.")

    def _on_chon_thu_muc_bai_lam(self) -> None:
        path = filedialog.askdirectory(title="Chọn thư mục chứa ảnh bài làm của lớp")
        if not path:
            return
        added, msg = self.controller.them_thu_muc_bai_lam(path)
        self.var_so_luong_bai.set(f"Đã chọn {len(self.controller.danh_sach_bai_lam)} ảnh bài làm.")
        self.var_trang_thai.set(msg)
        messagebox.showinfo("Thông báo", msg)

    def _on_chup_webcam(self) -> None:
        """Mở cửa sổ chụp ảnh trực tiếp từ camera (hỗ trợ cả USB và điện thoại qua Wi-Fi/cáp)."""
        camera_ip = self.var_camera_ip.get().strip()

        def _xu_ly_anh_da_chup(duong_dan: str):
            """Callback khi chụp xong 1 ảnh – thêm ảnh vào danh sách bài làm và cập nhật giao diện."""
            self.controller.them_anh_bai_lam(duong_dan)
            so_bai = len(self.controller.danh_sach_bai_lam)
            self.var_so_luong_bai.set(f"Đã chọn {so_bai} ảnh bài làm.")
            self.var_trang_thai.set(f"Đã chụp ảnh bài làm: {os.path.basename(duong_dan)} (Tổng số: {so_bai} bài)")

        # Mở cửa sổ chụp ảnh Tkinter – cho phép chọn nguồn, đổi camera hoặc nhập IP ngay trong cửa sổ
        CuaSoChupAnh(
            self.root,
            thu_muc_luu="outputs",
            camera_index=0,
            camera_ip_url=camera_ip,
            on_chup_xong=_xu_ly_anh_da_chup,
        )

    def _on_xoa_danh_sach(self) -> None:
        self.controller.xoa_danh_sach_bai_lam()
        self.tree_ket_qua.delete(*self.tree_ket_qua.get_children())
        self.tree_cau.delete(*self.tree_cau.get_children())
        self.var_so_luong_bai.set("Chưa có bài làm nào.")
        self.var_trang_thai.set("Đã xóa danh sách bài làm.")
        self._anh_goc_full_rgb = None
        self._anh_cham_full_rgb = None
        self._ten_anh_hien_tai = ""
        self.lbl_anh_goc.configure(image="", text="Chưa có ảnh gốc\n(Nhấp chuột hoặc bấm Phóng to để xem chi tiết)")
        self.lbl_anh_cham.configure(image="", text="Chưa có ảnh đã chấm\n(Nhấp chuột hoặc bấm Phóng to để xem chi tiết)")

    # -------------------------------------------------------------------------
    # SỰ KIỆN CHẤM BÀI ĐA LUỒNG (THREADING)
    # -------------------------------------------------------------------------
    def _on_bat_dau_cham(self) -> None:
        """Bắt đầu chấm bài trên luồng riêng để không đơ giao diện."""
        if not self.controller.tu_dien_dap_an:
            messagebox.showwarning(
                "Yêu cầu đáp án mẫu",
                "Chưa có đáp án mẫu chuẩn!\n\nVui lòng nạp ảnh đáp án mẫu ở BƯỚC 1 trước khi chấm bài làm của học sinh."
            )
            return

        if not self.controller.danh_sach_bai_lam:
            messagebox.showwarning(
                "Chưa có bài làm",
                "Chưa có ảnh bài làm nào trong danh sách!\n\nVui lòng chọn ảnh hoặc thư mục bài làm ở BƯỚC 2."
            )
            return

        self.btn_cham.configure(state=tk.DISABLED, text="Đang chấm bài...")
        self.var_tien_do.set(0.0)
        self.tree_ket_qua.delete(*self.tree_ket_qua.get_children())

        # Chạy trong luồng riêng
        thread = threading.Thread(target=self._worker_cham_bai, daemon=True)
        thread.start()

    def _worker_cham_bai(self) -> None:
        t_start = time.time()

        def _progress(curr: int, total: int, filename: str):
            percent = (curr / total) * 100.0
            self.root.after(0, lambda: self._update_progress(percent, curr, total, filename))

        try:
            results = self.controller.cham_tat_ca(progress_cb=_progress)
            t_total = time.time() - t_start
            self.root.after(0, lambda: self._on_cham_hoan_tat(results, t_total))
        except Exception as e:
            self.root.after(0, lambda: self._on_cham_that_bai(str(e)))

    def _update_progress(self, percent: float, curr: int, total: int, filename: str) -> None:
        self.var_tien_do.set(percent)
        self.var_trang_thai.set(f"Đang chấm [{curr}/{total}]: {filename} ({percent:.1f}%)")

    def _on_cham_hoan_tat(self, results: list[dict[str, Any]], t_total: float) -> None:
        self.btn_cham.configure(state=tk.NORMAL, text="BẮT ĐẦU CHẤM BÀI")
        self.var_tien_do.set(100.0)

        # Cập nhật Treeview kết quả
        self._cap_nhat_bang_ket_qua()

        so_da_cham = sum(1 for r in results if r["trang_thai"] == TRANG_THAI_DA_CHAM)
        so_loi = sum(1 for r in results if r["trang_thai"] == TRANG_THAI_LOI_ANH)
        so_chua_cham = sum(1 for r in results if r["trang_thai"] == TRANG_THAI_CHUA_CHAM)
        tb = (t_total / len(results)) if results else 0.0

        msg = f"Đã chấm xong {len(results)} bài trong {t_total:.2f}s (TB: {tb:.2f}s/bài). Hợp lệ: {so_da_cham} | Chưa khớp mã đề: {so_chua_cham} | Lỗi: {so_loi}"
        self.var_trang_thai.set(msg)

        # Tự động chọn dòng đầu tiên
        if self.tree_ket_qua.get_children():
            first_item = self.tree_ket_qua.get_children()[0]
            self.tree_ket_qua.selection_set(first_item)
            self.tree_ket_qua.focus(first_item)
            self._on_chon_dong_ket_qua()

        messagebox.showinfo("Chấm hoàn tất", msg)

    def _on_cham_that_bai(self, err_msg: str) -> None:
        self.btn_cham.configure(state=tk.NORMAL, text="BẮT ĐẦU CHẤM BÀI")
        self.var_trang_thai.set(f"Lỗi: {err_msg}")
        messagebox.showerror("Lỗi chấm bài", f"Đã xảy ra lỗi: {err_msg}")

    def _cap_nhat_bang_ket_qua(self) -> None:
        """Nạp dữ liệu vào bảng danh sách bài đã chấm."""
        self.tree_ket_qua.delete(*self.tree_ket_qua.get_children())
        for idx, r in enumerate(self.controller.danh_sach_ket_qua):
            stt = idx + 1
            ten = r.get("ten_anh_bai_lam", "")
            sbd = r.get("sbd", "????")
            md = r.get("ma_de", "???")
            dung = r.get("so_dung", 0)
            sai = r.get("so_sai", 0)
            diem = f"{r.get('diem', 0.0):.2f}"
            tt = r.get("trang_thai", "")

            # Nhãn trạng thái tiếng Việt
            if tt == TRANG_THAI_DA_CHAM:
                tt_str = "ĐÃ CHẤM"
            elif tt == TRANG_THAI_CHUA_CHAM:
                tt_str = "CHƯA CHẤM"
            else:
                tt_str = "LỖI ẢNH"

            if r.get("nghi_trung_bai"):
                tt_str += " (TRÙNG)"

            item_id = self.tree_ket_qua.insert(
                "", tk.END,
                values=(stt, ten, sbd, md, dung, sai, diem, tt_str)
            )

    # -------------------------------------------------------------------------
    # HIỂN THỊ CHI TIẾT & SỬA TAY KHI CHỌN DÒNG
    # -------------------------------------------------------------------------
    def _on_chon_dong_ket_qua(self, event=None) -> None:
        sel = self.tree_ket_qua.selection()
        if not sel:
            return
        idx = self.tree_ket_qua.index(sel[0])
        self.controller.bai_hien_tai_idx = idx
        self._hien_thi_chi_tiet_bai(idx)

    def _hien_thi_chi_tiet_bai(self, idx: int) -> None:
        if not (0 <= idx < len(self.controller.danh_sach_ket_qua)):
            return

        res = self.controller.danh_sach_ket_qua[idx]
        self.entry_sbd.delete(0, tk.END)
        self.entry_sbd.insert(0, res.get("sbd", ""))

        self.entry_made.delete(0, tk.END)
        self.entry_made.insert(0, res.get("ma_de", ""))

        # 1. Hiển thị bảng 50 câu
        self.tree_cau.delete(*self.tree_cau.get_children())
        ma_de = res.get("ma_de")
        da_chuan = self.controller.tu_dien_dap_an.get(ma_de, {}).get("answers")

        chi_tiet_50 = res.get("chi_tiet_50_cau", [])
        for i, item in enumerate(chi_tiet_50):
            cau_so = item.get("cau", i + 1)
            chon = item.get("lua_chon", "")
            chuan = da_chuan[i] if (da_chuan and i < len(da_chuan)) else "--"
            kq = item.get("ket_qua", "")

            # Gắn nhãn
            if kq == "DUNG":
                kq_str = "ĐÚNG"
            elif kq == "SAI":
                kq_str = "SAI"
            elif kq == "BLANK":
                kq_str = "TRỐNG"
            elif kq == "MULTI":
                kq_str = "TÔ NHIỀU"
            elif kq == "AMBIGUOUS":
                kq_str = "NGHI NGỜ"
            else:
                kq_str = "--"

            self.tree_cau.insert("", tk.END, values=(cau_so, chon, chuan, kq_str))

        # 2. Hiển thị ảnh gốc & ảnh đã chấm
        self._cap_nhat_anh_xem_truoc(res)

    def _cap_nhat_anh_xem_truoc(self, res: dict[str, Any]) -> None:
        """Cập nhật hai khung ảnh: ảnh gốc bên trái, ảnh đã chấm bên phải."""
        file_path = res.get("file_path", "")
        if not os.path.isfile(file_path):
            self._anh_goc_full_rgb = None
            self._anh_cham_full_rgb = None
            self.lbl_anh_goc.configure(image="", text="Không tìm thấy file ảnh gốc")
            self.lbl_anh_cham.configure(image="", text="Không có ảnh đã chấm")
            return

        # 1. Đọc và thu nhỏ ảnh gốc
        img_bgr = doc_anh_unicode(file_path)
        if img_bgr is not None:
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            self._anh_goc_full_rgb = img_rgb
            self._ten_anh_hien_tai = res.get("ten_anh_bai_lam", os.path.basename(file_path))
            self._photo_goc = self._chuyen_pil_sang_photo(img_rgb, max_w=380, max_h=320)
            self.lbl_anh_goc.configure(image=self._photo_goc, text="")
        else:
            self._anh_goc_full_rgb = None
            self.lbl_anh_goc.configure(image="", text="Lỗi đọc ảnh gốc")

        # 2. Tạo ảnh đã nắn và vẽ trực quan hóa kết quả
        try:
            cfg = self.controller.config
            warped, _, _ = xu_ly_va_nan_phieu(img_bgr, config=cfg)
            ma_de = res.get("ma_de")
            da_chuan = self.controller.tu_dien_dap_an.get(ma_de, {}).get("answers")
            diem = res.get("diem") if res.get("trang_thai") == TRANG_THAI_DA_CHAM else None

            vis = ve_anh_da_cham(
                warped,
                res.get("chi_tiet_50_cau", []),
                answers_chuan=da_chuan,
                sbd=res.get("sbd", "????"),
                ma_de=res.get("ma_de", "???"),
                diem=diem,
                config=cfg
            )
            vis_rgb = cv2.cvtColor(vis, cv2.COLOR_BGR2RGB)
            self._anh_cham_full_rgb = vis_rgb
            self._photo_cham = self._chuyen_pil_sang_photo(vis_rgb, max_w=380, max_h=320)
            self.lbl_anh_cham.configure(image=self._photo_cham, text="")
        except Exception as e:
            self._anh_cham_full_rgb = None
            self.lbl_anh_cham.configure(image="", text=f"Không thể nắn ảnh: {e}")

    def _chuyen_pil_sang_photo(self, rgb_arr: np.ndarray, max_w: int = 380, max_h: int = 320) -> ImageTk.PhotoImage:
        """Resize giữ tỉ lệ và chuyển mảng numpy RGB sang ImageTk."""
        h, w = rgb_arr.shape[:2]
        scale = min(max_w / float(w), max_h / float(h))
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))

        resized = cv2.resize(rgb_arr, (new_w, new_h), interpolation=cv2.INTER_AREA)
        pil_img = Image.fromarray(resized)
        return ImageTk.PhotoImage(pil_img)

    # -------------------------------------------------------------------------
    # CÁC HÀM PHÓNG TO ẢNH (ZOOM VIEWER)
    # -------------------------------------------------------------------------
    def _phong_to_anh_goc(self, event=None) -> None:
        """Mở cửa sổ phóng to độ phân giải cao cho ảnh bài làm gốc."""
        if self._anh_goc_full_rgb is None:
            messagebox.showinfo("Thông báo", "Chưa có ảnh bài làm gốc để phóng to.\nHãy chọn một bài làm trong bảng danh sách.")
            return
        tieu_de = f"Ảnh bài làm gốc – {self._ten_anh_hien_tai}"
        CuaSoPhongToAnh(self.root, self._anh_goc_full_rgb, tieu_de=tieu_de)

    def _phong_to_anh_cham(self, event=None) -> None:
        """Mở cửa sổ phóng to độ phân giải cao cho ảnh đã chấm (có dấu tích đúng/sai)."""
        if self._anh_cham_full_rgb is None:
            messagebox.showinfo("Thông báo", "Chưa có ảnh đã chấm để phóng to.\nHãy chọn một bài làm đã được chấm trong bảng danh sách.")
            return
        tieu_de = f"Ảnh bài làm đã chấm (Tích Đúng / Sai) – {self._ten_anh_hien_tai}"
        CuaSoPhongToAnh(self.root, self._anh_cham_full_rgb, tieu_de=tieu_de)

    def _phong_to_anh_mau(self, event=None) -> None:
        """Mở cửa sổ phóng to độ phân giải cao cho ảnh phiếu đáp án mẫu chuẩn."""
        if not self.controller.tu_dien_dap_an:
            messagebox.showinfo("Thông báo", "Chưa có đáp án mẫu nào được nạp.\nVui lòng chọn ảnh đáp án mẫu ở Bước 1.")
            return

        sel = self.tree_dap_an.selection()
        if sel:
            ma_de = str(self.tree_dap_an.item(sel[0], "values")[0])
        else:
            ma_de = list(self.controller.tu_dien_dap_an.keys())[0]

        info = self.controller.tu_dien_dap_an.get(ma_de)
        if not info:
            return

        file_path = info.get("file_path", "")
        img_bgr = None
        if os.path.isfile(file_path):
            img_bgr = doc_anh_unicode(file_path)

        if img_bgr is None and info.get("warped") is not None:
            img_bgr = info["warped"]

        if img_bgr is None:
            messagebox.showerror("Lỗi", f"Không tìm thấy file ảnh đáp án mẫu: {file_path}")
            return

        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        source_name = info.get("source_image", os.path.basename(file_path))
        tieu_de = f"Ảnh phiếu đáp án mẫu chuẩn – Mã đề {ma_de} ({source_name})"
        CuaSoPhongToAnh(self.root, img_rgb, tieu_de=tieu_de)

    def _on_luu_sbd_made(self) -> None:
        """Sửa tay SBD và Mã đề, chấm lại bài làm."""
        idx = self.controller.bai_hien_tai_idx
        if not (0 <= idx < len(self.controller.danh_sach_ket_qua)):
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một bài làm trong bảng danh sách.")
            return

        new_sbd = self.entry_sbd.get().strip()
        new_made = self.entry_made.get().strip()

        self.controller.sua_tay_sbd(idx, new_sbd)
        self.controller.sua_tay_ma_de(idx, new_made)

        self._cap_nhat_bang_ket_qua()
        # Giữ lại vị trí chọn
        children = self.tree_ket_qua.get_children()
        if 0 <= idx < len(children):
            self.tree_ket_qua.selection_set(children[idx])
            self._hien_thi_chi_tiet_bai(idx)

        messagebox.showinfo("Cập nhật", f"Đã cập nhật SBD: {new_sbd}, Mã đề: {new_made} và tính lại điểm.")

    def _on_double_click_cau(self, event=None) -> None:
        """Bấm đúp vào 1 câu trong bảng chi tiết để sửa tay đáp án."""
        sel = self.tree_cau.selection()
        if not sel:
            return
        cau_so = int(self.tree_cau.item(sel[0], "values")[0])
        idx_cau_0 = cau_so - 1
        bai_idx = self.controller.bai_hien_tai_idx

        # Hộp thoại chọn nhanh đáp án A/B/C/D hoặc Bỏ trống
        dlg = tk.Toplevel(self.root)
        dlg.title(f"Sửa câu {cau_so}")
        dlg.geometry("300x160")
        dlg.transient(self.root)
        dlg.grab_set()

        curr_opt = self.tree_cau.item(sel[0], "values")[1]
        ttk.Label(dlg, text=f"Sửa đáp án cho Câu {cau_so}:", font=self.font_dam).pack(pady=10)

        v_opt = tk.StringVar(value=curr_opt if curr_opt in ("A", "B", "C", "D") else "BLANK")
        cb = ttk.Combobox(dlg, textvariable=v_opt, values=["A", "B", "C", "D", "BLANK"], state="readonly", width=8)
        cb.pack(pady=6)

        def _apply():
            val = v_opt.get()
            self.controller.sua_tay_dap_an(bai_idx, idx_cau_0, val)
            self._cap_nhat_bang_ket_qua()
            children = self.tree_ket_qua.get_children()
            if 0 <= bai_idx < len(children):
                self.tree_ket_qua.selection_set(children[bai_idx])
                self._hien_thi_chi_tiet_bai(bai_idx)
            dlg.destroy()

        btn_box = ttk.Frame(dlg)
        btn_box.pack(fill=tk.X, pady=10, padx=20)
        ttk.Button(btn_box, text="Xác nhận", style="Success.TButton", command=_apply).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_box, text="Hủy", command=dlg.destroy).pack(side=tk.RIGHT)

    # -------------------------------------------------------------------------
    # XUẤT EXCEL & SQLITE
    # -------------------------------------------------------------------------
    def _on_xuat_excel(self) -> None:
        if not self.controller.danh_sach_ket_qua:
            messagebox.showwarning("Cảnh báo", "Chưa có dữ liệu kết quả để xuất. Hãy chấm bài trước.")
            return

        default_name = "ketqua.xlsx"
        path = filedialog.asksaveasfilename(
            title="Lưu file Excel kết quả chấm",
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[("Excel Workbook", "*.xlsx"), ("Tất cả", "*.*")]
        )
        if not path:
            return

        try:
            out = self.controller.xuat_ket_qua_excel(path)
            self.var_trang_thai.set(f"Đã xuất file Excel: {out}")
            messagebox.showinfo("Thành công", f"Đã xuất kết quả ra file Excel:\n{out}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xuất file Excel: {e}")

    def _on_xuat_sqlite(self) -> None:
        if not self.controller.danh_sach_ket_qua:
            messagebox.showwarning("Cảnh báo", "Chưa có dữ liệu kết quả để lưu. Hãy chấm bài trước.")
            return

        default_name = "ketqua.db"
        path = filedialog.asksaveasfilename(
            title="Lưu cơ sở dữ liệu SQLite",
            defaultextension=".db",
            initialfile=default_name,
            filetypes=[("SQLite Database", "*.db *.sqlite"), ("Tất cả", "*.*")]
        )
        if not path:
            return

        try:
            out = self.controller.xuat_ket_qua_sqlite(path)
            self.var_trang_thai.set(f"Đã lưu cơ sở dữ liệu SQLite: {out}")
            messagebox.showinfo("Thành công", f"Đã lưu kết quả ra database SQLite:\n{out}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu cơ sở dữ liệu: {e}")


def chup_man_hinh_cua_so(root: tk.Tk, duong_dan_luu: str) -> str | None:
    """
    Chụp ảnh màn hình cửa sổ Tkinter và lưu vào file.
    Sử dụng ctypes Windows GDI PrintWindow để chụp cửa sổ ngay cả khi không có chuột/màn hình tương tác.
    """
    try:
        root.update()
        hwnd = root.winfo_id()
        w = max(100, root.winfo_width())
        h = max(100, root.winfo_height())

        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        hwnd_dc = user32.GetWindowDC(hwnd)
        mfc_dc = gdi32.CreateCompatibleDC(hwnd_dc)
        save_bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, w, h)
        gdi32.SelectObject(mfc_dc, save_bitmap)
        user32.PrintWindow(hwnd, mfc_dc, 2)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ('biSize', wintypes.DWORD),
                ('biWidth', wintypes.LONG),
                ('biHeight', wintypes.LONG),
                ('biPlanes', wintypes.WORD),
                ('biBitCount', wintypes.WORD),
                ('biCompression', wintypes.DWORD),
                ('biSizeImage', wintypes.DWORD),
                ('biXPelsPerMeter', wintypes.LONG),
                ('biYPelsPerMeter', wintypes.LONG),
                ('biClrUsed', wintypes.DWORD),
                ('biClrImportant', wintypes.DWORD)
            ]

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = w
        bmi.biHeight = -h
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        buf = (ctypes.c_ubyte * (w * h * 4))()
        gdi32.GetDIBits(mfc_dc, save_bitmap, 0, h, ctypes.byref(buf), ctypes.byref(bmi), 0)

        arr = np.ctypeslib.as_array(buf).reshape((h, w, 4))
        img = Image.fromarray(arr[:, :, [2, 1, 0]])

        os.makedirs(os.path.dirname(os.path.abspath(duong_dan_luu)), exist_ok=True)
        img.save(duong_dan_luu)

        gdi32.DeleteObject(save_bitmap)
        gdi32.DeleteDC(mfc_dc)
        user32.ReleaseDC(hwnd, hwnd_dc)
        return duong_dan_luu
    except Exception as e:
        print(f"Lỗi chụp màn hình: {e}")
        return None


def khoi_chay_gui() -> None:
    """Hàm khởi chạy cửa sổ giao diện chính."""
    root = tk.Tk()
    app = OMRMainWindow(root)

    # Đảm bảo tắt tiến trình sạch sẽ khi đóng cửa sổ
    def _on_close():
        root.quit()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.mainloop()


if __name__ == "__main__":
    khoi_chay_gui()
