import os

def count_lines(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except Exception as e:
        return 0

def scan_dir(directory):
    large_files = []
    exclude_dirs = {'node_modules', '.venv', '.git', '__pycache__', 'dist', 'build'}
    exclude_exts = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', '.tar', '.gz'}
    
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in exclude_exts:
                continue
            filepath = os.path.join(root, file)
            lines = count_lines(filepath)
            if lines > 200:
                large_files.append((filepath, lines))
    return large_files

if __name__ == '__main__':
    workspace = r"d:\Official\ario\ArioNex"
    print("Scanning for files with > 200 lines...")
    large_files = scan_dir(workspace)
    # sort by line count descending
    large_files.sort(key=lambda x: x[1], reverse=True)
    for path, lines in large_files:
        rel_path = os.path.relpath(path, workspace)
        print(f"{rel_path}: {lines} lines")
