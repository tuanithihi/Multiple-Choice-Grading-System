"""
export.py – Xuất kết quả chấm trắc nghiệm ra Excel và SQLite.

Chức năng:
    1. Xuất Excel (.xlsx) gồm 3 sheet:
        - "TongHop": Bảng tổng kết danh sách thí sinh, điểm, số đúng/sai/trống/nhiều.
        - "ChiTiet": Bảng chi tiết 50 câu của từng thí sinh, tô màu trực quan (xanh cho đúng, đỏ cho sai, vàng cho nghi ngờ).
        - "DapAn": Danh sách đáp án chuẩn đọc được từ ảnh mẫu theo từng mã đề để giáo viên đối chiếu.
    2. Xuất SQLite (.db) gồm 4 bảng:
        - dap_an_chuan: Lưu đáp án chuẩn theo mã đề.
        - thi_sinh: Lưu danh sách thí sinh (SBD, Mã đề).
        - bai_lam: Lưu kết quả chấm tổng hợp, hỗ trợ ghi đè (upsert) khi chấm lại cùng SBD+Mã đề.
        - chi_tiet_cau: Lưu chi tiết kết quả từng câu của bài làm.
"""

import os
import sqlite3
from typing import Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def xuat_excel(
    ds_ket_qua: list[dict[str, Any]],
    tu_dien_dap_an: dict[str, dict[str, Any]],
    duong_dan_excel: str = "outputs/ketqua.xlsx",
    ds_loi: list[dict[str, Any]] | None = None
) -> str:
    """
    Xuất báo cáo kết quả chấm trắc nghiệm ra file Excel với định dạng và màu sắc chuyên nghiệp.
    Bao gồm 4 sheet:
        - "TongHop": Bảng tổng hợp điểm số và trạng thái của tất cả bài làm, có cảnh báo trùng bài.
        - "ChiTiet": Bảng chi tiết kết quả từng câu hỏi (chỉ cho các bài đọc thành công).
        - "DapAn": Đáp án chuẩn theo từng mã đề để đối chiếu.
        - "Loi": Danh sách các ảnh bị lỗi (file hỏng, ảnh mờ/tối, không tìm thấy phiếu) kèm lý do.

    Args:
        ds_ket_qua: Danh sách kết quả chấm từ scoring.cham_danh_sach_bai().
        tu_dien_dap_an: Từ điển đáp án chuẩn {ma_de: {"answers": [50 đáp án], "source_image": ...}}.
        duong_dan_excel: Đường dẫn file Excel đầu ra.
        ds_loi: Danh sách lỗi bổ sung nếu có.

    Returns:
        str: Đường dẫn file Excel đã lưu thành công.
    """
    thu_muc = os.path.dirname(duong_dan_excel)
    if thu_muc and not os.path.exists(thu_muc):
        os.makedirs(thu_muc, exist_ok=True)

    wb = openpyxl.Workbook()

    # Định nghĩa kiểu dáng và màu sắc
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=11, bold=True)
    font_normal = Font(name="Calibri", size=11)

    fill_header = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    fill_header_loi = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")
    fill_sub_header = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")

    fill_dung = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")  # Xanh lá nhạt
    font_dung = Font(name="Calibri", size=11, color="006100", bold=True)

    fill_sai = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")   # Đỏ nhạt
    font_sai = Font(name="Calibri", size=11, color="9C0006")

    fill_amb = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")   # Vàng nhạt
    font_amb = Font(name="Calibri", size=11, color="806000")

    fill_multi = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid") # Cam nhạt
    font_multi = Font(name="Calibri", size=11, color="C65911")

    fill_blank = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid") # Xám nhạt
    font_blank = Font(name="Calibri", size=11, color="7F7F7F")

    border_thin = Side(border_style="thin", color="D3D3D3")
    border_all = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)

    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")

    # =========================================================================
    # SHEET 1: TongHop
    # =========================================================================
    ws_tong_hop = wb.active
    ws_tong_hop.title = "TongHop"

    tieu_de_th = [
        "STT", "Số báo danh", "Mã đề", "Số đúng", "Số sai",
        "Bỏ trống", "Tô nhiều", "Nghi ngờ", "Điểm số",
        "Ảnh bài làm", "Ảnh đáp án", "Trạng thái", "Ghi chú"
    ]
    ws_tong_hop.append(tieu_de_th)

    for col_num in range(1, len(tieu_de_th) + 1):
        cell = ws_tong_hop.cell(row=1, column=col_num)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center

    for idx, item in enumerate(ds_ket_qua, start=1):
        ghi_chu = item.get("ly_do", "") or ""
        if item.get("nghi_trung_bai"):
            cac_file_trung = item.get("file_trung", [])
            ghi_chu = f"⚠️ Nghi trùng bài với: {', '.join(cac_file_trung)}. " + ghi_chu

        row_vals = [
            idx,
            item.get("sbd", "????"),
            item.get("ma_de", "???"),
            item.get("so_dung", 0),
            item.get("so_sai", 0),
            item.get("so_blank", 0),
            item.get("so_multi", 0),
            item.get("so_ambiguous", 0),
            item.get("diem", 0.0),
            item.get("ten_anh_bai_lam", ""),
            item.get("ten_anh_dap_an", "") or "—",
            item.get("trang_thai", ""),
            ghi_chu
        ]
        ws_tong_hop.append(row_vals)
        current_row = ws_tong_hop.max_row
        for col_num in range(1, len(row_vals) + 1):
            cell = ws_tong_hop.cell(row=current_row, column=col_num)
            cell.font = font_normal
            cell.border = border_all
            cell.alignment = align_center if col_num in (1, 2, 3, 4, 5, 6, 7, 8, 9, 12) else align_left
            if col_num == 9:
                cell.font = font_bold

    # =========================================================================
    # SHEET 2: ChiTiet
    # =========================================================================
    ws_chi_tiet = wb.create_sheet(title="ChiTiet")

    tieu_de_ct = ["STT", "Số báo danh", "Mã đề", "Câu hỏi", "Lựa chọn HS", "Đáp án chuẩn", "Kết quả", "Đánh giá"]
    ws_chi_tiet.append(tieu_de_ct)
    for col_num in range(1, len(tieu_de_ct) + 1):
        cell = ws_chi_tiet.cell(row=1, column=col_num)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center

    stt_ct = 1
    for hs_item in ds_ket_qua:
        if hs_item.get("trang_thai") == "LOI_ANH":
            continue

        sbd = hs_item.get("sbd", "????")
        ma_de = hs_item.get("ma_de", "???")
        chi_tiet_cau = hs_item.get("chi_tiet_50_cau", [])

        for c_info in chi_tiet_cau:
            cau_so = c_info["cau"]
            lua_chon = c_info.get("lua_chon", "")
            da_chuan = c_info.get("dap_an_chuan", "") or "—"
            kq = c_info.get("ket_qua", "") or "—"

            danh_gia_str = ""
            if kq == "DUNG":
                danh_gia_str = "Đúng (+0.2)"
            elif kq == "SAI":
                danh_gia_str = "Sai"
            elif kq == "BLANK":
                danh_gia_str = "Bỏ trống"
            elif kq == "MULTI":
                danh_gia_str = "Tô nhiều ô"
            elif kq == "AMBIGUOUS":
                danh_gia_str = "Nghi ngờ / Cần xem lại"

            row_ct = [stt_ct, sbd, ma_de, f"Câu {cau_so:02d}", lua_chon, da_chuan, kq, danh_gia_str]
            ws_chi_tiet.append(row_ct)
            r_idx = ws_chi_tiet.max_row

            # Định dạng và tô màu theo kết quả
            for col_num in range(1, len(row_ct) + 1):
                cell = ws_chi_tiet.cell(row=r_idx, column=col_num)
                cell.font = font_normal
                cell.border = border_all
                cell.alignment = align_center

            # Tô màu cột Kết quả (cột 7) và Đánh giá (cột 8)
            cell_kq = ws_chi_tiet.cell(row=r_idx, column=7)
            cell_dg = ws_chi_tiet.cell(row=r_idx, column=8)

            if kq == "DUNG":
                cell_kq.fill = fill_dung
                cell_kq.font = font_dung
                cell_dg.fill = fill_dung
                cell_dg.font = font_dung
            elif kq == "SAI":
                cell_kq.fill = fill_sai
                cell_kq.font = font_sai
                cell_dg.fill = fill_sai
                cell_dg.font = font_sai
            elif kq == "BLANK":
                cell_kq.fill = fill_blank
                cell_kq.font = font_blank
            elif kq == "MULTI":
                cell_kq.fill = fill_multi
                cell_kq.font = font_multi
                cell_dg.fill = fill_multi
                cell_dg.font = font_multi
            elif kq == "AMBIGUOUS":
                cell_kq.fill = fill_amb
                cell_kq.font = font_amb
                cell_dg.fill = fill_amb
                cell_dg.font = font_amb
        stt_ct += 1

    # =========================================================================
    # SHEET 3: DapAn
    # =========================================================================
    ws_dap_an = wb.create_sheet(title="DapAn")

    # Liệt kê các mã đề hiện có
    danh_sach_ma_de = sorted(tu_dien_dap_an.keys())
    tieu_de_da = ["Câu hỏi"] + [f"Mã đề {md}\n({tu_dien_dap_an[md]['source_image']})" for md in danh_sach_ma_de]
    ws_dap_an.append(tieu_de_da)

    for col_num in range(1, len(tieu_de_da) + 1):
        cell = ws_dap_an.cell(row=1, column=col_num)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws_dap_an.row_dimensions[1].height = 32

    for q in range(1, 51):
        row_da = [f"Câu {q:02d}"]
        for md in danh_sach_ma_de:
            answers_list = tu_dien_dap_an[md]["answers"]
            da = answers_list[q - 1] if q - 1 < len(answers_list) else ""
            row_da.append(da)
        ws_dap_an.append(row_da)

        r_idx = ws_dap_an.max_row
        for col_num in range(1, len(row_da) + 1):
            cell = ws_dap_an.cell(row=r_idx, column=col_num)
            cell.font = font_bold if col_num > 1 else font_normal
            cell.border = border_all
            cell.alignment = align_center

    # =========================================================================
    # SHEET 4: Loi
    # =========================================================================
    ws_loi = wb.create_sheet(title="Loi")
    tieu_de_loi = ["STT", "Tên file", "Đường dẫn", "Loại lỗi", "Chi tiết lỗi"]
    ws_loi.append(tieu_de_loi)

    for col_num in range(1, len(tieu_de_loi) + 1):
        cell = ws_loi.cell(row=1, column=col_num)
        cell.font = font_header
        cell.fill = fill_header_loi
        cell.alignment = align_center

    # Thu thập danh sách ảnh lỗi
    danh_sach_loi_tong_hop = []
    if ds_loi:
        danh_sach_loi_tong_hop.extend(ds_loi)

    for item in ds_ket_qua:
        if item.get("trang_thai") == "LOI_ANH":
            danh_sach_loi_tong_hop.append({
                "ten_file": item.get("ten_anh_bai_lam", ""),
                "duong_dan": item.get("file_path", ""),
                "loai_loi": "Lỗi đọc / nắn phiếu",
                "chi_tiet": item.get("ly_do", "") or "; ".join(item.get("warnings", [])),
            })

    for idx, err in enumerate(danh_sach_loi_tong_hop, start=1):
        row_loi = [
            idx,
            err.get("ten_file", ""),
            err.get("duong_dan", ""),
            err.get("loai_loi", "Lỗi xử lý"),
            err.get("chi_tiet", "")
        ]
        ws_loi.append(row_loi)
        r_idx = ws_loi.max_row
        for col_num in range(1, len(row_loi) + 1):
            cell = ws_loi.cell(row=r_idx, column=col_num)
            cell.font = font_normal
            cell.border = border_all
            cell.alignment = align_center if col_num == 1 else align_left

    # Tự động căn chỉnh độ rộng cột cho cả 4 sheet
    for ws in (ws_tong_hop, ws_chi_tiet, ws_dap_an, ws_loi):
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                if "\n" in val_str:
                    val_str = max(val_str.split("\n"), key=len)
                if len(val_str) > max_len:
                    max_len = len(val_str)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    wb.save(duong_dan_excel)
    return duong_dan_excel


def xuat_sqlite(
    ds_ket_qua: list[dict[str, Any]],
    tu_dien_dap_an: dict[str, dict[str, Any]],
    duong_dan_db: str = "outputs/ketqua.db"
) -> str:
    """
    Xuất kết quả chấm trắc nghiệm vào cơ sở dữ liệu SQLite với 4 bảng chuẩn.
    Hỗ trợ chạy nhiều lần mà không bị nhân đôi bản ghi (upsert).

    Args:
        ds_ket_qua: Danh sách kết quả chấm.
        tu_dien_dap_an: Từ điển đáp án chuẩn.
        duong_dan_db: Đường dẫn file SQLite database.

    Returns:
        str: Đường dẫn file database đã ghi.
    """
    thu_muc = os.path.dirname(duong_dan_db)
    if thu_muc and not os.path.exists(thu_muc):
        os.makedirs(thu_muc, exist_ok=True)

    conn = sqlite3.connect(duong_dan_db)
    cursor = conn.cursor()

    # Kích hoạt hỗ trợ khóa ngoại
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Bảng dap_an_chuan
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dap_an_chuan (
            ma_de TEXT PRIMARY KEY,
            ten_anh TEXT,
            duong_dan TEXT,
            dap_an_chuoi TEXT,
            thoi_gian TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Bảng thi_sinh
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS thi_sinh (
            sbd TEXT,
            ma_de TEXT,
            PRIMARY KEY (sbd, ma_de)
        );
    """)

    # 3. Bảng bai_lam
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bai_lam (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sbd TEXT,
            ma_de TEXT,
            so_dung INTEGER,
            so_sai INTEGER,
            so_blank INTEGER,
            so_multi INTEGER,
            so_ambiguous INTEGER,
            diem REAL,
            ten_anh TEXT,
            ten_anh_dap_an TEXT,
            trang_thai TEXT,
            ly_do TEXT,
            thoi_gian TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(sbd, ma_de)
        );
    """)

    # 4. Bảng chi_tiet_cau
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chi_tiet_cau (
            bai_lam_id INTEGER,
            cau INTEGER,
            lua_chon TEXT,
            dap_an_chuan TEXT,
            ket_qua TEXT,
            can_xem_lai INTEGER,
            PRIMARY KEY (bai_lam_id, cau),
            FOREIGN KEY (bai_lam_id) REFERENCES bai_lam(id) ON DELETE CASCADE
        );
    """)

    # Ghi dữ liệu vào dap_an_chuan
    for md, da_info in tu_dien_dap_an.items():
        ans_str = "".join(da_info.get("answers", []))
        cursor.execute("""
            INSERT INTO dap_an_chuan (ma_de, ten_anh, duong_dan, dap_an_chuoi)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ma_de) DO UPDATE SET
                ten_anh = excluded.ten_anh,
                duong_dan = excluded.duong_dan,
                dap_an_chuoi = excluded.dap_an_chuoi,
                thoi_gian = CURRENT_TIMESTAMP;
        """, (md, da_info.get("source_image", ""), da_info.get("file_path", ""), ans_str))

    # Ghi dữ liệu bài làm của thí sinh
    for item in ds_ket_qua:
        if item.get("trang_thai") == "LOI_ANH":
            continue

        sbd = item.get("sbd", "????")
        ma_de = item.get("ma_de", "???")

        # Ghi thi_sinh
        cursor.execute("""
            INSERT OR IGNORE INTO thi_sinh (sbd, ma_de) VALUES (?, ?);
        """, (sbd, ma_de))

        # Kiểm tra xem bai_lam đã tồn tại chưa để cập nhật hoặc thêm mới
        cursor.execute("SELECT id FROM bai_lam WHERE sbd = ? AND ma_de = ?;", (sbd, ma_de))
        row = cursor.fetchone()

        if row:
            bai_lam_id = row[0]
            cursor.execute("""
                UPDATE bai_lam SET
                    so_dung = ?,
                    so_sai = ?,
                    so_blank = ?,
                    so_multi = ?,
                    so_ambiguous = ?,
                    diem = ?,
                    ten_anh = ?,
                    ten_anh_dap_an = ?,
                    trang_thai = ?,
                    ly_do = ?,
                    thoi_gian = CURRENT_TIMESTAMP
                WHERE id = ?;
            """, (
                item.get("so_dung", 0),
                item.get("so_sai", 0),
                item.get("so_blank", 0),
                item.get("so_multi", 0),
                item.get("so_ambiguous", 0),
                item.get("diem", 0.0),
                item.get("ten_anh_bai_lam", ""),
                item.get("ten_anh_dap_an", ""),
                item.get("trang_thai", ""),
                item.get("ly_do", ""),
                bai_lam_id
            ))
            # Xóa chi tiết cũ để nạp lại
            cursor.execute("DELETE FROM chi_tiet_cau WHERE bai_lam_id = ?;", (bai_lam_id,))
        else:
            cursor.execute("""
                INSERT INTO bai_lam (
                    sbd, ma_de, so_dung, so_sai, so_blank, so_multi, so_ambiguous,
                    diem, ten_anh, ten_anh_dap_an, trang_thai, ly_do
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                sbd,
                ma_de,
                item.get("so_dung", 0),
                item.get("so_sai", 0),
                item.get("so_blank", 0),
                item.get("so_multi", 0),
                item.get("so_ambiguous", 0),
                item.get("diem", 0.0),
                item.get("ten_anh_bai_lam", ""),
                item.get("ten_anh_dap_an", ""),
                item.get("trang_thai", ""),
                item.get("ly_do", "")
            ))
            bai_lam_id = cursor.lastrowid

        # Ghi bảng chi_tiet_cau
        for c_info in item.get("chi_tiet_50_cau", []):
            cau = c_info["cau"]
            lua_chon = c_info.get("lua_chon", "")
            da_chuan = c_info.get("dap_an_chuan", "")
            kq = c_info.get("ket_qua", "")
            can_xem_lai = 1 if c_info.get("can_xem_lai") else 0

            cursor.execute("""
                INSERT INTO chi_tiet_cau (bai_lam_id, cau, lua_chon, dap_an_chuan, ket_qua, can_xem_lai)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (bai_lam_id, cau, lua_chon, da_chuan, kq, can_xem_lai))

    conn.commit()
    conn.close()
    return duong_dan_db
