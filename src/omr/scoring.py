"""
scoring.py – Chấm điểm bài làm học sinh dựa trên từ điển đáp án chuẩn cùng mã đề.

Quy trình:
    1. Đọc ảnh bài làm học sinh thông qua read_sheet() để lấy SBD, Mã đề và 50 câu trả lời.
    2. Tìm đáp án chuẩn CÙNG MÃ ĐỀ trong từ điển đáp án mẫu.
    3. Nếu không có đáp án chuẩn hoặc mã đề chứa "?":
        -> Trạng thái "CHƯA CHẤM - [Lý do]", vẫn ghi nhận SBD và đáp án thô.
        -> Cho phép nhập mã đề bằng tay (qua override_made).
    4. So sánh từng câu: ĐÚNG / SAI / BỎ TRỐNG / TÔ NHIỀU / NGHI NGỜ.
    5. Tính điểm: số câu đúng * điểm mỗi câu (mặc định 0.2), làm tròn 2 chữ số thập phân.
"""

import time
import os
from typing import Any

from omr.config import nap_config
from omr.read_sheet import read_sheet
from omr.grade_logic import (
    TRANG_THAI_HOP_LE,
    TRANG_THAI_BLANK,
    TRANG_THAI_MULTI,
    TRANG_THAI_AMBIGUOUS,
)


KET_QUA_DUNG = "DUNG"
KET_QUA_SAI = "SAI"
KET_QUA_BLANK = "BLANK"
KET_QUA_MULTI = "MULTI"
KET_QUA_AMBIGUOUS = "AMBIGUOUS"

TRANG_THAI_DA_CHAM = "DA_CHAM"
TRANG_THAI_CHUA_CHAM = "CHUA_CHAM"
TRANG_THAI_LOI_ANH = "LOI_ANH"


def tinh_diem_50_cau(
    answers_hoc_sinh: list[dict[str, Any]],
    answers_chuan: list[str],
    diem_moi_cau: float = 0.2
) -> tuple[int, int, int, int, int, float, list[dict[str, Any]]]:
    """
    So sánh 50 câu học sinh với đáp án chuẩn và tính điểm.

    Args:
        answers_hoc_sinh: Danh sách 50 dict kết quả câu hỏi.
        answers_chuan: Danh sách 50 ký tự đáp án chuẩn ('A'..'D').
        diem_moi_cau: Điểm cho mỗi câu đúng (mặc định 0.2).

    Returns:
        tuple: (so_dung, so_sai, so_blank, so_multi, so_ambiguous, diem, chi_tiet_50_cau)
    """
    so_dung = 0
    so_sai = 0
    so_blank = 0
    so_multi = 0
    so_amb = 0
    chi_tiet = []

    for idx, item in enumerate(answers_hoc_sinh):
        q = item.get("cau", idx + 1)
        opt = item.get("lua_chon", "")
        st = item.get("trang_thai", "")
        da_dung = answers_chuan[idx] if idx < len(answers_chuan) else None

        can_xem_lai = False
        if opt == "BLANK" or st == TRANG_THAI_BLANK:
            so_blank += 1
            kq = KET_QUA_BLANK
        elif opt == "MULTI" or st == TRANG_THAI_MULTI:
            so_multi += 1
            kq = KET_QUA_MULTI
        elif opt == "AMBIGUOUS" or st == TRANG_THAI_AMBIGUOUS:
            so_amb += 1
            kq = KET_QUA_AMBIGUOUS
            can_xem_lai = True
        else:
            if da_dung is not None and opt == da_dung:
                so_dung += 1
                kq = KET_QUA_DUNG
            else:
                so_sai += 1
                kq = KET_QUA_SAI

        cau_dict = dict(item)
        cau_dict.update({
            "cau": q,
            "lua_chon": opt,
            "dap_an_chuan": da_dung,
            "ket_qua": kq,
            "can_xem_lai": can_xem_lai,
        })
        chi_tiet.append(cau_dict)

    diem = round(so_dung * diem_moi_cau, 2)
    return so_dung, so_sai, so_blank, so_multi, so_amb, diem, chi_tiet


def cham_mot_bai(
    anh_bai_lam: str,
    tu_dien_dap_an: dict[str, dict[str, Any]],
    config: dict | None = None,
    override_made: str | None = None,
    debug: bool = False
) -> dict[str, Any]:
    """
    Chấm điểm 1 bài làm của học sinh từ đường dẫn ảnh.
    Bắt mọi ngoại lệ nếu file bị hỏng hoặc không phát hiện được phiếu, đảm bảo không sập chương trình.

    Args:
        anh_bai_lam: Đường dẫn tới file ảnh bài làm học sinh.
        tu_dien_dap_an: Từ điển đáp án chuẩn {ma_de: {"answers": [50 đáp án], "source_image": ...}}.
        config: Dict cấu hình hệ thống.
        override_made: Mã đề nhập tay để ghi đè (nếu mã đề trên phiếu bị mờ hoặc học sinh quên tô).
        debug: Có xuất ảnh trực quan không.

    Returns:
        Dict kết quả chấm:
            - 'sbd': str
            - 'ma_de': str
            - 'ma_de_goc': str
            - 'so_dung': int
            - 'so_sai': int
            - 'so_blank': int
            - 'so_multi': int
            - 'so_ambiguous': int
            - 'diem': float
            - 'ma_de_khop': bool
            - 'ten_anh_bai_lam': str
            - 'ten_anh_dap_an': str | None
            - 'trang_thai': 'DA_CHAM', 'CHUA_CHAM' hoặc 'LOI_ANH'
            - 'ly_do': str | None
            - 'chi_tiet_50_cau': list[dict]
            - 'warnings': list[str]
            - 'file_path': str
            - 'thoi_gian_xu_ly': float (giây)
    """
    t_start = time.time()
    ten_anh = os.path.basename(anh_bai_lam)

    if config is None:
        config = nap_config()

    diem_cfg = config.get("diem", {})
    diem_moi_cau = float(diem_cfg.get("diem_moi_cau", 0.2))

    # 1. Đọc phiếu qua read_sheet() kèm bắt lỗi an toàn cho toàn bộ lô
    try:
        res_sheet = read_sheet(anh_bai_lam, config=config, debug=debug)
    except Exception as e:
        thoi_gian_loi = round(time.time() - t_start, 3)
        return {
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
            "ten_anh_bai_lam": ten_anh,
            "ten_anh_dap_an": None,
            "trang_thai": TRANG_THAI_LOI_ANH,
            "ly_do": f"Lỗi đọc ảnh / không tìm thấy phiếu: {e}",
            "chi_tiet_50_cau": [],
            "warnings": [str(e)],
            "file_path": anh_bai_lam,
            "thoi_gian_xu_ly": thoi_gian_loi,
        }

    sbd = res_sheet["sbd"]
    ma_de_doc_duoc = res_sheet["ma_de"]
    answers_50 = res_sheet["answers"]
    warnings = list(res_sheet["warnings"])

    # 2. Xử lý override mã đề nếu được cung cấp
    if override_made is not None and str(override_made).strip():
        ma_de = str(override_made).strip()
    else:
        ma_de = ma_de_doc_duoc

    # 3. Kiểm tra tính hợp lệ của mã đề và tìm đáp án chuẩn
    da_chuan_info = None
    ly_do_chua_cham = None

    if not ma_de or "?" in ma_de:
        ly_do_chua_cham = f"Mã đề không đọc được hoặc không đầy đủ ('{ma_de}'). Yêu cầu nhập tay mã đề."
    elif ma_de not in tu_dien_dap_an:
        ds_ma_de_co = ", ".join(tu_dien_dap_an.keys()) if tu_dien_dap_an else "Không có"
        ly_do_chua_cham = f"Không tìm thấy đáp án chuẩn cho mã đề '{ma_de}' (các mã đề hiện có: {ds_ma_de_co})."
    else:
        da_chuan_info = tu_dien_dap_an[ma_de]

    # 4. Nếu KHÔNG tìm được đáp án chuẩn -> Trả về trạng thái CHƯA CHẤM
    if da_chuan_info is None:
        chi_tiet_50 = []
        so_blank = 0
        so_multi = 0
        so_amb = 0

        for item in answers_50:
            st = item["trang_thai"]
            opt = item["lua_chon"]
            if st == TRANG_THAI_BLANK:
                so_blank += 1
                kq = KET_QUA_BLANK
            elif st == TRANG_THAI_MULTI:
                so_multi += 1
                kq = KET_QUA_MULTI
            elif st == TRANG_THAI_AMBIGUOUS:
                so_amb += 1
                kq = KET_QUA_AMBIGUOUS
            else:
                kq = None

            chi_tiet_50.append({
                "cau": item["cau"],
                "lua_chon": opt,
                "dap_an_chuan": None,
                "ket_qua": kq,
                "can_xem_lai": (st == TRANG_THAI_AMBIGUOUS),
            })

        return {
            "sbd": sbd,
            "ma_de": ma_de,
            "ma_de_goc": ma_de_doc_duoc,
            "so_dung": 0,
            "so_sai": 0,
            "so_blank": so_blank,
            "so_multi": so_multi,
            "so_ambiguous": so_amb,
            "diem": 0.0,
            "ma_de_khop": False,
            "ten_anh_bai_lam": ten_anh,
            "ten_anh_dap_an": None,
            "trang_thai": TRANG_THAI_CHUA_CHAM,
            "ly_do": ly_do_chua_cham,
            "chi_tiet_50_cau": chi_tiet_50,
            "warnings": warnings,
            "file_path": anh_bai_lam,
            "thoi_gian_xu_ly": round(time.time() - t_start, 3),
        }

    # 5. So sánh từng câu và tính điểm
    dap_an_chuan_50 = da_chuan_info["answers"]
    ten_anh_dap_an = da_chuan_info["source_image"]

    so_dung = 0
    so_sai = 0
    so_blank = 0
    so_multi = 0
    so_amb = 0
    chi_tiet_50 = []

    for idx, item in enumerate(answers_50):
        q = item["cau"]
        opt = item["lua_chon"]
        st = item["trang_thai"]
        da_dung = dap_an_chuan_50[idx]

        can_xem_lai = False

        if st == TRANG_THAI_BLANK:
            so_blank += 1
            kq = KET_QUA_BLANK
        elif st == TRANG_THAI_MULTI:
            so_multi += 1
            kq = KET_QUA_MULTI
        elif st == TRANG_THAI_AMBIGUOUS:
            so_amb += 1
            kq = KET_QUA_AMBIGUOUS
            can_xem_lai = True
        else:  # TRANG_THAI_HOP_LE
            if opt == da_dung:
                so_dung += 1
                kq = KET_QUA_DUNG
            else:
                so_sai += 1
                kq = KET_QUA_SAI

        chi_tiet_50.append({
            "cau": q,
            "lua_chon": opt,
            "dap_an_chuan": da_dung,
            "ket_qua": kq,
            "can_xem_lai": can_xem_lai,
        })

    tong_diem = round(so_dung * diem_moi_cau, 2)

    return {
        "sbd": sbd,
        "ma_de": ma_de,
        "ma_de_goc": ma_de_doc_duoc,
        "so_dung": so_dung,
        "so_sai": so_sai,
        "so_blank": so_blank,
        "so_multi": so_multi,
        "so_ambiguous": so_amb,
        "diem": tong_diem,
        "ma_de_khop": True,
        "ten_anh_bai_lam": ten_anh,
        "ten_anh_dap_an": ten_anh_dap_an,
        "trang_thai": TRANG_THAI_DA_CHAM,
        "ly_do": None,
        "chi_tiet_50_cau": chi_tiet_50,
        "warnings": warnings,
        "file_path": anh_bai_lam,
        "thoi_gian_xu_ly": round(time.time() - t_start, 3),
    }


def cham_danh_sach_bai(
    ds_anh_bai_lam: list[str],
    tu_dien_dap_an: dict[str, dict[str, Any]],
    config: dict | None = None,
    override_made_map: dict[str, str] | None = None,
    debug: bool = False
) -> list[dict[str, Any]]:
    """
    Chấm hàng loạt danh sách ảnh bài làm học sinh.
    Tự động ghi nhận thời gian từng bài và phát hiện nghi trùng bài (cùng SBD + Mã đề).
    """
    if config is None:
        config = nap_config()

    if override_made_map is None:
        override_made_map = {}

    ket_qua_danh_sach = []
    for path in ds_anh_bai_lam:
        ten_file = os.path.basename(path)
        override_val = override_made_map.get(ten_file, override_made_map.get(path, None))
        res = cham_mot_bai(
            path,
            tu_dien_dap_an=tu_dien_dap_an,
            config=config,
            override_made=override_val,
            debug=debug
        )
        ket_qua_danh_sach.append(res)

    # Phát hiện và cảnh báo khi hai ảnh bài làm có cùng SBD + Mã đề (nghi trùng bài)
    sbd_made_groups: dict[tuple[str, str], list[int]] = {}
    for idx, res in enumerate(ket_qua_danh_sach):
        sbd = res.get("sbd", "????")
        md = res.get("ma_de", "???")
        if sbd != "????" and md != "???" and "?" not in sbd and "?" not in md and res.get("trang_thai") != TRANG_THAI_LOI_ANH:
            key = (sbd, md)
            sbd_made_groups.setdefault(key, []).append(idx)

    for (sbd, md), indices in sbd_made_groups.items():
        if len(indices) > 1:
            ten_files = [ket_qua_danh_sach[i]["ten_anh_bai_lam"] for i in indices]
            for i in indices:
                item = ket_qua_danh_sach[i]
                cac_file_khac = [f for f in ten_files if f != item["ten_anh_bai_lam"]]
                msg = f"Nghi trùng bài: SBD {sbd} và Mã đề {md} trùng lặp với ảnh {', '.join(cac_file_khac)}"
                item["warnings"].append(msg)
                item["nghi_trung_bai"] = True
                item["file_trung"] = cac_file_khac

    return ket_qua_danh_sach

