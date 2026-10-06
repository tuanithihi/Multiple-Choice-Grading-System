"""
answer_key.py – Dựng từ điển đáp án chuẩn từ ảnh phiếu đáp án mẫu.

Đáp án chuẩn được đọc trực tiếp từ ảnh phiếu đáp án mẫu thông qua hàm read_sheet()
(không nhập tay, không dùng file trung gian).

Quy trình:
    1. Quét thư mục ảnh đáp án mẫu (data/answer_key_images/).
    2. Với mỗi ảnh, gọi read_sheet() để lấy Mã đề và 50 đáp án.
    3. KIỂM TRA CHẤT LƯỢNG NGHIÊM NGẶT:
        - Mã đề phải đầy đủ chữ số, không chứa ký tự "?".
        - Toàn bộ 50 câu phải là đáp án đơn hợp lệ A/B/C/D (không có BLANK, MULTI, AMBIGUOUS).
        - Mỗi mã đề chỉ được có DUY NHẤT một ảnh đáp án mẫu (chống trùng lặp).
    4. Trả về từ điển: {ma_de: {"answers": [50 đáp án], "source_image": tên_file, ...}}
"""

import os
from typing import Any

from omr.config import nap_config
from omr.samples import liet_ke_anh_thu_muc
from omr.read_sheet import read_sheet
from omr.grade_logic import TRANG_THAI_HOP_LE


class LoiDapAnMau(Exception):
    """Ngoại lệ khi ảnh đáp án mẫu không đạt chất lượng kiểm định."""
    pass


def dung_tu_dien_dap_an(
    thu_muc_dap_an: str = "data/answer_key_images",
    config: dict | None = None,
    override_ma_de: dict[str, str] | str | None = None,
    debug: bool = False
) -> dict[str, dict[str, Any]]:
    """
    Quét thư mục ảnh đáp án mẫu và dựng từ điển đáp án chuẩn theo từng mã đề.

    Args:
        thu_muc_dap_an: Đường dẫn thư mục chứa ảnh đáp án mẫu (mặc định: data/answer_key_images).
        config: Dict cấu hình hệ thống.
        override_ma_de: Mã đề ghi đè nếu ảnh đáp án mẫu để trống mã đề. Có thể là:
            - str: áp dụng cho ảnh duy nhất trong thư mục.
            - dict: ánh xạ {tên_file: mã_đề}, ví dụ {"Mẫu GV.png": "567"}.
        debug: Có xuất ảnh trực quan không.

    Returns:
        Dict:
            {
                ma_de: {
                    "ma_de": str,
                    "answers": list[str],          # 50 ký tự 'A'..'D'
                    "answers_raw": list[dict],      # 50 dict chi tiết
                    "source_image": str,            # Tên file ảnh
                    "file_path": str,               # Đường dẫn đầy đủ
                }
            }

    Raises:
        LoiDapAnMau: Khi thư mục trống, mã đề không hợp lệ, câu hỏi lỗi hoặc trùng mã đề.
    """
    if config is None:
        config = nap_config()

    if not os.path.isdir(thu_muc_dap_an):
        raise LoiDapAnMau(f"Không tìm thấy thư mục đáp án mẫu: {thu_muc_dap_an}")

    ds_file = liet_ke_anh_thu_muc(thu_muc_dap_an)
    ds_hop_le = [f for f in ds_file if f["hop_le"]]

    if not ds_hop_le:
        raise LoiDapAnMau(f"Thư mục '{thu_muc_dap_an}' không chứa file ảnh đáp án mẫu hợp lệ nào.")

    tu_dien_dap_an: dict[str, dict[str, Any]] = {}

    for info in ds_hop_le:
        ten_file = info["ten_file"]
        duong_dan = info["duong_dan"]

        # 1. Đọc phiếu qua read_sheet()
        try:
            res = read_sheet(duong_dan, config=config, debug=debug)
        except Exception as e:
            raise LoiDapAnMau(f"Lỗi khi xử lý ảnh đáp án mẫu '{ten_file}': {e}") from e

        ma_de = res["sbd"] if False else res["ma_de"]  # lấy mã đề từ phiếu
        answers_50 = res["answers"]

        # 2. Xử lý ghi đè mã đề nếu có cấu hình
        if override_ma_de is not None:
            if isinstance(override_ma_de, str):
                ma_de = override_ma_de.strip()
            elif isinstance(override_ma_de, dict):
                if ten_file in override_ma_de:
                    ma_de = override_ma_de[ten_file].strip()
                elif os.path.basename(ten_file) in override_ma_de:
                    ma_de = override_ma_de[os.path.basename(ten_file)].strip()

        # 3. KIỂM TRA CHẤT LƯỢNG MÃ ĐỀ
        if not ma_de or "?" in ma_de or len(ma_de) != 3 or not ma_de.isdigit():
            raise LoiDapAnMau(
                f"Ảnh đáp án mẫu '{ten_file}': Mã đề không hợp lệ ('{ma_de}'). "
                f"Mã đề trên phiếu mẫu phải có đủ 3 chữ số và không chứa ký tự '?'. "
                f"Yêu cầu giáo viên chụp lại hoặc sử dụng tham số --override-key-made."
            )

        # 4. KIỂM TRA TRÙNG MÃ ĐỀ
        if ma_de in tu_dien_dap_an:
            file_da_co = tu_dien_dap_an[ma_de]["source_image"]
            raise LoiDapAnMau(
                f"Trùng mã đề '{ma_de}': Phát hiện ở cả 2 file '{file_da_co}' và '{ten_file}'. "
                f"Mỗi mã đề chỉ được có DUY NHẤT một ảnh đáp án mẫu chuẩn."
            )

        # 5. KIỂM TRA CHẤT LƯỢNG 50 CÂU HỎI
        if len(answers_50) != 50:
            raise LoiDapAnMau(
                f"Ảnh đáp án mẫu '{ten_file}': Không đọc đủ 50 câu hỏi (chỉ đọc được {len(answers_50)} câu)."
            )

        danh_sach_dap_an_chuoi: list[str] = []
        for item in answers_50:
            q = item["cau"]
            opt = item["lua_chon"]
            st = item["trang_thai"]

            if st != TRANG_THAI_HOP_LE or opt not in ("A", "B", "C", "D"):
                raise LoiDapAnMau(
                    f"Ảnh đáp án mẫu '{ten_file}': Câu {q} có trạng thái '{st}' (lựa chọn: '{opt}'). "
                    f"Toàn bộ 50 câu trên phiếu đáp án mẫu phải được tô đơn rõ ràng (A/B/C/D). "
                    f"Yêu cầu giáo viên kiểm tra và chụp lại phiếu mẫu."
                )
            danh_sach_dap_an_chuoi.append(opt)

        tu_dien_dap_an[ma_de] = {
            "ma_de": ma_de,
            "answers": danh_sach_dap_an_chuoi,
            "answers_raw": answers_50,
            "source_image": ten_file,
            "file_path": duong_dan,
        }

    return tu_dien_dap_an
