"""
/// <summary>
/// اسکریپت تست تجمیعی سراسری و کنترل کیفیت نهایی آریونکس (ArioNex Global Test Runner)
/// </summary>
/// <remarks>
/// این اسکریپت به عنوان اجراکننده مرکزی (Runner) تمامی پرونده‌های تست فازهای پیشین
/// (فازهای ۲، ۳، ۴ و ۵) را به صورت متوالی و کنترل شده در فرآیندهای فرعی (Subprocesses)
/// اجرا نموده و تاییدیه سلامت نهایی سامانه را پیش از استقرار صادر می‌نماید.
/// </remarks>
"""

import sys
import os
import subprocess

def run_test_script(script_name: str) -> bool:
    """
    /// <summary>
    /// اجرای یک اسکریپت تست در فرآیند فرعی سیستم
    /// </summary>
    /// <param name="script_name">نام فایل اسکریپت تست مستقر در پوشه tests</param>
    /// <returns>مقدار منطقی نشان‌دهنده موفقیت یا شکست اجرای تست</returns>
    """
    tests_dir = os.path.dirname(__file__)
    script_path = os.path.join(tests_dir, script_name)
    
    print(f"\n🏃 Running Test Suite: {script_name}...")
    print("-" * 50)
    
    # تنظیم انکودینگ خروجی ترمینال جهت نمایش بی نقص متون فارسی
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    try:
        # اجرای اسکریپت تست و هدایت خروجی‌ها به کنسول اصلی
        result = subprocess.run(
            [sys.executable, script_path],
            env=env,
            capture_output=False,
            text=True,
            check=True
        )
        print("-" * 50)
        print(f"✅ Test Suite {script_name} Completed Successfully (Exit Code: {result.returncode}).")
        return True
    except subprocess.CalledProcessError as e:
        print("-" * 50)
        print(f"❌ Test Suite {script_name} Failed with Exit Code: {e.returncode}!")
        return False
    except Exception as ex:
        print("-" * 50)
        print(f"❌ Unexpected error running {script_name}: {str(ex)}")
        return False

def main():
    print("=========================================")
    print("STARTING ARIOPLEX GLOBAL INTEGRATION TESTS")
    print("=========================================")
    
    # لیست سناریوهای تستی فازهای ۲ تا ۵
    test_suites = [
        "test_phase2.py",
        "test_phase3.py",
        "test_phase4.py",
        "test_phase5.py"
    ]
    
    success_count = 0
    failed_suites = []
    
    for suite in test_suites:
        if run_test_script(suite):
            success_count += 1
        else:
            failed_suites.append(suite)
            
    print("\n=========================================")
    print("           GRAND TEST SUMMARY            ")
    print("=========================================")
    print(f"Total Suites Executed: {len(test_suites)}")
    print(f"Passed:                {success_count} / {len(test_suites)}")
    print(f"Failed:                {len(failed_suites)}")
    
    if failed_suites:
        print(f"Failed Suites List:   {failed_suites}")
        print("\n❌ SYSTEM INTEGRATION VERIFICATION FAILED!")
        print("Please check the errors logged above and fix issues before releasing.")
        print("=========================================")
        sys.exit(1)
    else:
        print("\n🌟 ALL ARIOPLEX CORE SYSTEM TESTS PASSED SUCCESSFULLY! 🌟")
        print("Your ArioNex application is fully stable and ready for production deployment.")
        print("=========================================")
        sys.exit(0)

if __name__ == "__main__":
    main()
