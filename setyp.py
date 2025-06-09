import os
import subprocess
import sys

REQUIRED_PYTHON_MAJOR = 3
REQUIRED_PYTHON_MINOR = 8
REQUIRED_PACKAGES = [
    "requests",
    "jinja2"
]

# Usage:  python3 APISequenceRunner.py sequence1 test2

def check_python_version():
    print("Checking Python version...")
    if sys.version_info.major < REQUIRED_PYTHON_MAJOR or \
       (sys.version_info.major == REQUIRED_PYTHON_MAJOR and sys.version_info.minor < REQUIRED_PYTHON_MINOR):
        sys.exit(f"Python {REQUIRED_PYTHON_MAJOR}.{REQUIRED_PYTHON_MINOR}+ is required. You are using {sys.version}")
    print(f"Python version {sys.version.split()[0]} is OK.")

def install_packages():
    print("Installing required packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", *REQUIRED_PACKAGES])
    print("All packages installed successfully.")

def main():
    check_python_version()
    install_packages()
    print("\nSetup complete. You can now run the script using:")
    print("  python script.py <sequence_name>")

if __name__ == "__main__":
    main()
