"""
main.py – Điểm vào chương trình chấm phiếu trắc nghiệm OMR.

Cách dùng:
    python main.py --help
    python main.py --student-image data/student_images/Hs1.png
    python main.py --student-dir data/student_images --out-excel outputs/ketqua.xlsx
    python main.py --key-dir data/answer_key_images --student-dir data/student_images --debug
"""

import argparse
import io
import os
import sys

# Đảm bảo stdout/stderr dùng UTF-8 trên Windows (tránh lỗi cp1252)
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Tắt cảnh báo ồn ào của OpenCV trên Windows (obsensor / UVC index)
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"

# Thêm thư mục src vào đường dẫn import
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import cv2
try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
except Exception:
    pass

from omr.config import nap_config
from omr.samples import doc_anh_unicode, kiem_tra_anh, liet_ke_anh_thu_muc
from omr.warp import xu_ly_va_nan_phieu, ve_kiem_tra_roi
from omr.detect_sheet import LoiKhongTimThayPhieu


def tao_parser() -> argparse.ArgumentParser:
    """Tạo bộ phân tích tham số dòng lệnh."""
    parser = argparse.ArgumentParser(
        prog="OMR Chấm trắc nghiệm",
        description="Chấm phiếu trả lời trắc nghiệm 50 câu từ ảnh chụp.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
  python main.py --student-image data/student_images/Hs1.png
  python main.py --student-dir data/student_images --out-excel outputs/ketqua.xlsx
  python main.py --student-dir data/student_images --out-db outputs/ketqua.db --debug
        """,
    )

    parser.add_argument(
        "--key-dir",
        type=str,
        default="data/answer_key_images",
        help="Thư mục chứa ảnh phiếu đáp án mẫu (mặc định: data/answer_key_images).",
    )

    # Nhóm ảnh bài làm: chọn 1 ảnh hoặc cả thư mục
    nhom_anh = parser.add_mutually_exclusive_group()
    nhom_anh.add_argument(
        "--student-image",
        type=str,
        help="Đường dẫn tới 1 ảnh bài làm của học sinh.",
    )
    nhom_anh.add_argument(
        "--student-dir",
        type=str,
        default=None,
        help="Thư mục chứa ảnh bài làm (mặc định: data/student_images).",
    )

    parser.add_argument(
        "--override-made",
        type=str,
        default=None,
        help="Ghi đè mã đề học sinh nếu bài làm bị mờ hoặc học sinh quên tô mã đề.",
    )

    parser.add_argument(
        "--override-key-made",
        type=str,
        default="567",
        help="Ghi đè mã đề cho ảnh đáp án mẫu (mặc định: '567' nếu ảnh mẫu để trống mã đề).",
    )

    parser.add_argument(
        "--webcam",
        action="store_true",
        help="Chụp ảnh bài làm của học sinh trực tiếp từ webcam/camera.",
    )

    parser.add_argument(
        "--camera-ip",
        type=str,
        default=None,
        help="URL stream camera IP của điện thoại (ví dụ: http://192.168.1.15:4747/video).",
    )

    parser.add_argument(
        "--camera-index",
        type=int,
        default=0,
        help="Chỉ số camera USB (mặc định: 0).",
    )

    parser.add_argument(
        "--out-excel",
        type=str,
        default=None,
        help="Đường dẫn file Excel xuất kết quả (ví dụ: outputs/ketqua.xlsx).",
    )

    parser.add_argument(
        "--out-db",
        type=str,
        default=None,
        help="Đường dẫn file SQLite xuất kết quả (ví dụ: outputs/ketqua.db).",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Bật chế độ debug: lưu ảnh trung gian ra outputs/debug/.",
    )

    parser.add_argument(
        "--gui",
        action="store_true",
        help="Khởi chạy giao diện đồ họa người dùng Tkinter trực quan.",
    )

    parser.add_argument(
        "--cli",
        action="store_true",
        help="Chạy ở chế độ dòng lệnh (CLI) thay vì mở giao diện đồ họa.",
    )

    return parser


def kiem_tra_thu_muc(duong_dan: str, ten_mo_ta: str) -> bool:
    """Kiểm tra thư mục tồn tại."""
    if not os.path.isdir(duong_dan):
        print(f"❌ Lỗi: Không tìm thấy thư mục {ten_mo_ta}: {duong_dan}")
        return False
    print(f"✅ Thư mục {ten_mo_ta}: {duong_dan}")
    return True


def ve_minh_hoa_bo_cuc(duong_dan_anh: str, config: dict, thu_muc_debug: str = "outputs/debug") -> str | None:
    """Vẽ các ROI lên ảnh để kiểm tra trực quan bố cục."""
    import cv2
    from omr.preprocess import luu_anh_debug

    anh = doc_anh_unicode(duong_dan_anh)
    if anh is None:
        return None

    vis = anh.copy()

    # 1. Vẽ 4 Marker góc (Xanh dương)
    for k, m in config.get("markers_goc", {}).items():
        if k.startswith("_"):
            continue
        x, y, w, h = m["x"], m["y"], m["w"], m["h"]
        cv2.rectangle(vis, (x, y), (x + w, y + h), (255, 0, 0), 2)
        cv2.putText(vis, k, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

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

    ten_goc = os.path.splitext(os.path.basename(duong_dan_anh))[0]
    ten_debug = f"layout_preview_{ten_goc}.png"
    return luu_anh_debug(vis, ten_debug, thu_muc_debug)


def in_danh_sach_anh(danh_sach: list[dict], ten_loai: str):
    """In danh sách ảnh chi tiết kèm kích thước và trạng thái."""
    print(f"\n📁 Danh sách {ten_loai}: ({len(danh_sach)} file)")
    if not danh_sach:
        print("   (Không có file ảnh nào)")
        return

    for idx, info in enumerate(danh_sach, start=1):
        ten = info["ten_file"]
        dung_luong_kb = info["dung_luong_bytes"] / 1024
        if info["hop_le"]:
            w, h, c = info["chieu_rong"], info["chieu_cao"], info["so_kenh"]
            print(f"   [{idx}] {ten}: {w}×{h} px, {c} kênh, {dung_luong_kb:.1f} KB -> ✅ Hợp lệ")
        else:
            loi = info.get("loi", "Lỗi không xác định")
            print(f"   [{idx}] {ten}: {dung_luong_kb:.1f} KB -> ❌ Lỗi ({loi})")


def main():
    """Hàm chính – xử lý tham số dòng lệnh và điều phối chương trình."""
    import time
    parser = tao_parser()
    args = parser.parse_args()

    # Mặc định khởi chạy giao diện Tkinter nếu có cờ --gui HOẶC chạy không truyền tham số nào
    if args.gui or (len(sys.argv) == 1 and not getattr(args, "cli", False)):
        from omr.gui import khoi_chay_gui
        khoi_chay_gui()
        return

    print("=" * 60)
    print("  OMR – Chấm phiếu trả lời trắc nghiệm từ ảnh")
    print("  Mẫu THPT 50 câu (A/B/C/D)")
    print("=" * 60)

    # 1. Nạp cấu hình
    try:
        config = nap_config()
        print("✅ Nạp cấu hình thành công.")
        if config.get("chua_xac_nhan"):
            print("⚠️  Cấu hình đang ở chế độ NHÁP (chưa xác nhận bố cục phiếu).")
        else:
            print("✅ Cấu hình bố cục: ĐÃ XÁC NHẬN (chua_xac_nhan: false)")
    except Exception as e:
        print(f"❌ Lỗi nạp cấu hình: {e}")
        sys.exit(1)

    # 2. Xử lý tùy chọn chụp từ camera/webcam/điện thoại nếu được yêu cầu
    if args.webcam or args.camera_ip:
        from omr.webcam import chup_anh_tu_webcam
        captured_path = chup_anh_tu_webcam(
            camera_index=args.camera_index,
            camera_ip_url=args.camera_ip,
        )
        if captured_path:
            args.student_image = captured_path
        else:
            print("ℹ️  Kết thúc do không có ảnh chụp từ camera.")
            return

    # 3. Kiểm tra và nạp ảnh thư mục đáp án mẫu
    if not kiem_tra_thu_muc(args.key_dir, "đáp án mẫu"):
        sys.exit(1)

    ds_dap_an = liet_ke_anh_thu_muc(args.key_dir)
    in_danh_sach_anh(ds_dap_an, "ảnh đáp án mẫu")
    so_da_hop_le = sum(1 for a in ds_dap_an if a["hop_le"])

    # 4. Xử lý ảnh bài làm học sinh
    ds_bai_lam: list[dict] = []
    if args.student_image:
        print(f"\n📄 Chế độ: chấm 1 ảnh bài làm")
        info = kiem_tra_anh(args.student_image)
        if not info["ton_tai"]:
            print(f"❌ Lỗi: Không tìm thấy file: {args.student_image}")
            sys.exit(1)
        if not info["hop_le"]:
            print(f"❌ Lỗi: Không đọc được ảnh: {info['loi']}")
            sys.exit(1)
        w, h, c = info["chieu_rong"], info["chieu_cao"], info["so_kenh"]
        kb = info["dung_luong_bytes"] / 1024
        print(f"✅ Đọc ảnh thành công: {info['ten_file']}")
        print(f"   Kích thước: {w} × {h} pixel, {c} kênh, {kb:.1f} KB -> Hợp lệ")
        ds_bai_lam = [info]

    elif args.student_dir:
        print(f"\n📁 Chế độ: quét thư mục bài làm ({args.student_dir})")
        if not kiem_tra_thu_muc(args.student_dir, "bài làm"):
            sys.exit(1)
        ds_bai_lam = liet_ke_anh_thu_muc(args.student_dir)
        in_danh_sach_anh(ds_bai_lam, "ảnh bài làm học sinh")

    else:
        mac_dinh = "data/student_images"
        print(f"\n📁 Chế độ: quét thư mục bài làm mặc định ({mac_dinh})")
        if os.path.isdir(mac_dinh):
            ds_bai_lam = liet_ke_anh_thu_muc(mac_dinh)
            in_danh_sach_anh(ds_bai_lam, "ảnh bài làm học sinh")
        else:
            print(f"⚠️  Thư mục mặc định không tồn tại: {mac_dinh}")

    # 5. Dựng đáp án chuẩn từ ảnh mẫu (Chỉ thực hiện MỘT LẦN duy nhất)
    from omr.answer_key import dung_tu_dien_dap_an, LoiDapAnMau
    from omr.scoring import cham_mot_bai, TRANG_THAI_LOI_ANH
    from omr.export import xuat_excel, xuat_sqlite

    print("\n" + "=" * 60)
    print("  BƯỚC 1: DỰNG TỪ ĐIỂN ĐÁP ÁN CHUẨN TỪ ẢNH MẪU")
    print("=" * 60)

    try:
        tu_dien_dap_an = dung_tu_dien_dap_an(
            args.key_dir,
            config=config,
            override_ma_de=args.override_key_made,
            debug=args.debug
        )
        print(f"✅ Đã dựng thành công đáp án chuẩn cho {len(tu_dien_dap_an)} mã đề:")
        for md, info in tu_dien_dap_an.items():
            ans_str = "".join(info["answers"])
            print(f"   - Mã đề {md} (từ '{info['source_image']}'): {ans_str[:25]}...{ans_str[25:]}")
    except LoiDapAnMau as e:
        print(f"❌ Lỗi đáp án mẫu: {e}")
        tu_dien_dap_an = {}

    print("\n" + "=" * 60)
    print("  BƯỚC 2: CHẤM BÀI LÀM CỦA HỌC SINH")
    print("=" * 60)

    ds_ket_qua = []
    t_batch_start = time.time()

    for a in ds_bai_lam:
        if a["hop_le"]:
            res = cham_mot_bai(
                a["duong_dan"],
                tu_dien_dap_an=tu_dien_dap_an,
                config=config,
                override_made=args.override_made,
                debug=args.debug
            )
        else:
            # File hỏng, file rỗng hoặc không phải ảnh -> Đóng gói bản ghi LOI_ANH để xuất sheet Loi
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
                "ten_anh_bai_lam": a.get("ten_file", ""),
                "ten_anh_dap_an": None,
                "trang_thai": TRANG_THAI_LOI_ANH,
                "ly_do": f"File không đọc được hoặc không hợp lệ: {a.get('loi', 'Lỗi không xác định')}",
                "chi_tiet_50_cau": [],
                "warnings": [a.get("loi", "File không hợp lệ")],
                "file_path": a.get("duong_dan", ""),
                "thoi_gian_xu_ly": 0.0,
            }

        ds_ket_qua.append(res)
        stt = len(ds_ket_qua)
        sbd = res["sbd"]
        md = res["ma_de"]
        diem = res["diem"]
        tt = res["trang_thai"]
        t_xu_ly = res.get("thoi_gian_xu_ly", 0.0)

        if tt == "DA_CHAM":
            dung = res["so_dung"]
            sai = res["so_sai"]
            blank = res["so_blank"]
            amb = res["so_ambiguous"]
            print(f"[{stt:02d}] {a['ten_file']:<15} | SBD: {sbd:<5} | Mã đề: {md:<4} | Đúng: {dung:02d} | Sai: {sai:02d} | Trống: {blank:02d} | Nghi ngờ: {amb:02d} | ĐIỂM: {diem:4.2f} | ⏱️ {t_xu_ly:.2f}s ✅")

            # Tạo và lưu ảnh bài làm có dấu tích đúng/sai vào outputs/
            try:
                import cv2
                from omr.gui import ve_anh_da_cham
                img_raw = doc_anh_unicode(a["duong_dan"])
                if img_raw is not None:
                    warped, _, _ = xu_ly_va_nan_phieu(img_raw, config=config)
                    da_chuan_list = tu_dien_dap_an.get(md, {}).get("answers")
                    vis_da_cham = ve_anh_da_cham(
                        warped,
                        res.get("chi_tiet_50_cau", []),
                        answers_chuan=da_chuan_list,
                        sbd=sbd,
                        ma_de=md,
                        diem=diem,
                        config=config
                    )
                    ten_khong_dau = os.path.splitext(a["ten_file"])[0]
                    out_img_name = f"da_cham_{ten_khong_dau}.png"
                    out_img_path = os.path.join("outputs", out_img_name)
                    cv2.imencode(".png", vis_da_cham)[1].tofile(out_img_path)
                    print(f"     📸 Ảnh bài làm có dấu tích đúng/sai: {out_img_path}")
            except Exception as e_anh:
                pass
        elif tt == "CHUA_CHAM":
            print(f"[{stt:02d}] {a['ten_file']:<15} | SBD: {sbd:<5} | Mã đề: {md:<4} | ⚠️  {res['ly_do']} | ⏱️ {t_xu_ly:.2f}s")
        else:  # LOI_ANH
            print(f"[{stt:02d}] {a['ten_file']:<15} | ❌ LỖI ẢNH: {res['ly_do']} | ⏱️ {t_xu_ly:.2f}s")

    # Phát hiện nghi trùng bài (cùng SBD + Mã đề)
    sbd_made_map: dict[tuple[str, str], list[int]] = {}
    for idx, r in enumerate(ds_ket_qua):
        sbd = r.get("sbd", "????")
        md = r.get("ma_de", "???")
        if sbd != "????" and md != "???" and "?" not in sbd and "?" not in md and r.get("trang_thai") != TRANG_THAI_LOI_ANH:
            key = (sbd, md)
            sbd_made_map.setdefault(key, []).append(idx)

    for (sbd, md), idx_list in sbd_made_map.items():
        if len(idx_list) > 1:
            all_files = [ds_ket_qua[i]["ten_anh_bai_lam"] for i in idx_list]
            print(f"\n⚠️  CẢNH BÁO TRÙNG BÀI: SBD {sbd} và Mã đề {md} xuất hiện trên {len(idx_list)} bài làm:")
            for i in idx_list:
                item = ds_ket_qua[i]
                cac_file_khac = [f for f in all_files if f != item["ten_anh_bai_lam"]]
                item["nghi_trung_bai"] = True
                item["file_trung"] = cac_file_khac
                print(f"   - {item['ten_anh_bai_lam']} (trùng với {', '.join(cac_file_khac)})")

    t_batch_total = time.time() - t_batch_start
    so_luong_bai = len(ds_bai_lam)
    thoi_gian_tb = (t_batch_total / so_luong_bai) if so_luong_bai > 0 else 0.0

    print(f"\n⏱️  Tổng thời gian xử lý: {t_batch_total:.2f} giây")
    print(f"⏱️  Thời gian trung bình mỗi phiếu: {thoi_gian_tb:.3f} giây/phiếu (Yêu cầu <= 3.0s)")

    # 6. Xuất kết quả
    file_excel = args.out_excel or "outputs/ketqua.xlsx"
    file_db = args.out_db or "outputs/ketqua.db"

    print("\n" + "=" * 60)
    print("  BƯỚC 3: XUẤT KẾT QUẢ")
    print("=" * 60)

    if ds_ket_qua:
        path_excel = xuat_excel(ds_ket_qua, tu_dien_dap_an, file_excel)
        print(f"📊 Đã xuất file Excel: {path_excel} (bao gồm sheet 'TongHop', 'ChiTiet', 'DapAn', 'Loi')")

        path_db = xuat_sqlite(ds_ket_qua, tu_dien_dap_an, file_db)
        print(f"🗄️  Đã lưu cơ sở dữ liệu SQLite: {path_db}")

    so_da_cham = sum(1 for r in ds_ket_qua if r["trang_thai"] == "DA_CHAM")
    so_loi = sum(1 for r in ds_ket_qua if r["trang_thai"] == TRANG_THAI_LOI_ANH)
    print("\n" + "=" * 60)
    print(f"  Tổng kết: Đã chấm {len(ds_ket_qua)} bài làm | Thành công: {so_da_cham} | Lỗi: {so_loi}")
    print("  Giai đoạn 7: Tăng độ bền và chấm hàng loạt hoàn tất.")
    print("=" * 60)


if __name__ == "__main__":
    main()

