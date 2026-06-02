"""
/// <summary>
/// اسکریپت ایندکس‌سازی دسته‌ای داده‌های محلی آریونکس (ArioNex Local Batch Ingest Script)
/// </summary>
/// <remarks>
/// این اسکریپت به دولوپران اجازه می‌دهد بدون راه‌اندازی FastAPI یا داشبورد React،
/// فایل‌های موجود در پوشه‌های data/unstructured، data/structured و data/qna را
/// مستقیماً پردازش و ایندکس کنند.
///
/// نحوه اجرا:
///   cd backend
///   python scripts/ingest_local_data.py --type all
///   python scripts/ingest_local_data.py --type unstructured
///   python scripts/ingest_local_data.py --type qna
///   python scripts/ingest_local_data.py --type structured
/// </remarks>
"""

import sys
import os
import argparse
import logging

# اضافه کردن مسیر بک‌اند به sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# اطمینان از فعال بودن حالت محلی
os.environ.setdefault("USE_LOCAL_DATA_DIR", "true")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from app.core.logging import setup_logging
setup_logging()
logger = logging.getLogger("arionex.ingest_script")


def ingest_unstructured():
    """پردازش و ایندکس‌سازی اسناد متنی، PDF و Word از data/unstructured/"""
    from app.core.local_storage import ingest_from_data_directory
    from app.services.workers.unstructured_processor import unstructured_processor

    print("\n" + "="*60)
    print("  ایندکس‌سازی اسناد بدون ساختار (Unstructured Documents)")
    print("="*60)

    results = ingest_from_data_directory(
        file_type="unstructured",
        processor_fn=unstructured_processor.process_document,
        start_file_id=1000
    )

    passed = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]

    print(f"\n  نتیجه: {len(passed)} موفق | {len(failed)} ناموفق از {len(results)} فایل")
    for r in failed:
        print(f"  [!] خطا در '{r['file']}': {r['error']}")
    return len(failed) == 0


def ingest_qna():
    """پردازش و ایندکس‌سازی فایل‌های CSV پرسش و پاسخ از data/qna/"""
    from app.core.local_storage import ingest_from_data_directory
    from app.services.workers.qna_processor import qna_processor

    print("\n" + "="*60)
    print("  ایندکس‌سازی الگوهای پرسش و پاسخ (QnA Templates)")
    print("="*60)

    results = ingest_from_data_directory(
        file_type="qna",
        processor_fn=qna_processor.process_qna_csv,
        start_file_id=2000
    )

    passed = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]

    print(f"\n  نتیجه: {len(passed)} موفق | {len(failed)} ناموفق از {len(results)} فایل")
    for r in failed:
        print(f"  [!] خطا در '{r['file']}': {r['error']}")
    return len(failed) == 0


def ingest_structured():
    """اعتبارسنجی و بایگانی فایل‌های مالی CSV/Excel از data/structured/"""
    from app.core.local_storage import ingest_from_data_directory
    from app.services.workers.structured_processor import structured_processor

    print("\n" + "="*60)
    print("  اعتبارسنجی داده‌های ساختاریافته مالی (Structured/Financial Data)")
    print("="*60)

    results = ingest_from_data_directory(
        file_type="structured",
        processor_fn=structured_processor.process_structured_csv,
        start_file_id=3000
    )

    passed = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]

    print(f"\n  نتیجه: {len(passed)} موفق | {len(failed)} ناموفق از {len(results)} فایل")
    for r in failed:
        print(f"  [!] خطا در '{r['file']}': {r['error']}")
    return len(failed) == 0


def list_data_contents():
    """لیست محتوای فعلی تمام دایرکتوری‌های داده"""
    from app.core.local_storage import list_data_directory, DATA_ROOT_DIR

    print("\n" + "="*60)
    print("  محتوای دایرکتوری‌های داده محلی آریونکس")
    print(f"  مسیر ریشه: {DATA_ROOT_DIR}")
    print("="*60)

    for dtype in ["unstructured", "structured", "qna"]:
        files = list_data_directory(dtype)
        print(f"\n  data/{dtype}/  ({len(files)} فایل)")
        if files:
            for f in files:
                size_kb = f["size_bytes"] / 1024
                print(f"    - {f['name']}  ({size_kb:.1f} KB)")
        else:
            print(f"    (خالی - فایل‌های مرتبط را در این پوشه قرار دهید)")


def main():
    parser = argparse.ArgumentParser(
        description="ArioNex Local Data Batch Ingestor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
مثال‌های استفاده:
  python scripts/ingest_local_data.py --type all
  python scripts/ingest_local_data.py --type unstructured
  python scripts/ingest_local_data.py --type qna
  python scripts/ingest_local_data.py --type structured
  python scripts/ingest_local_data.py --list
        """
    )
    parser.add_argument(
        "--type",
        choices=["all", "unstructured", "qna", "structured"],
        default="all",
        help="نوع داده برای ایندکس‌سازی (پیش‌فرض: all)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="نمایش لیست فایل‌های موجود در دایرکتوری‌های داده"
    )

    args = parser.parse_args()

    print("\n" + "="*60)
    print("  ArioNex Local Batch Data Ingestor")
    print("  (حالت: Local Data Directory - MinIO غیرفعال)")
    print("="*60)

    if args.list:
        list_data_contents()
        return

    all_ok = True

    if args.type in ("all", "unstructured"):
        ok = ingest_unstructured()
        all_ok = all_ok and ok

    if args.type in ("all", "qna"):
        ok = ingest_qna()
        all_ok = all_ok and ok

    if args.type in ("all", "structured"):
        ok = ingest_structured()
        all_ok = all_ok and ok

    print("\n" + "="*60)
    if all_ok:
        print("  تمام فایل‌ها با موفقیت ایندکس شدند.")
    else:
        print("  برخی فایل‌ها با خطا مواجه شدند. لاگ‌های بالا را بررسی کنید.")
    print("="*60 + "\n")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
