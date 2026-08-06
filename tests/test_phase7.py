"""
/// <summary>
/// ArioNex global aggregated test script and final quality control (ArioNex Global Test Runner)
/// </summary>
/// <remarks>
/// This script acts as the central runner for all test files from the previous phases
/// (phases 2, 3, 4, and 5), executing them sequentially and in a controlled manner in subprocesses,
/// and issues the final system health approval before deployment.
/// </remarks>
"""

import sys
import os
import subprocess

def run_test_script(script_name: str) -> bool:
    """
    /// <summary>
    /// Run a test script in a system subprocess
    /// </summary>
    /// <param name="script_name">Name of the test script file located in the tests folder</param>
    /// <returns>A boolean value indicating the success or failure of the test run</returns>
    """
    tests_dir = os.path.dirname(__file__)
    script_path = os.path.join(tests_dir, script_name)
    
    print(f"\n🏃 Running Test Suite: {script_name}...")
    print("-" * 50)
    
    # Set the terminal output encoding for flawless display of Persian text
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    try:
        # Run the test script and direct its output to the main console
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
    
    # List of test scenarios for phases 2 through 5 and phase 8
    test_suites = [
        "test_phase2.py",
        "test_phase3.py",
        "test_phase4.py",
        "test_phase5.py",
        "test_phase8.py"
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
