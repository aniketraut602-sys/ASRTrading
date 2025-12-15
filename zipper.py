
import os
import zipfile

def create_linux_zip(folders, output_filename, extra_files=None):
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for folder in folders:
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if "__pycache__" in root: continue
                    file_path = os.path.join(root, file)
                    arcname = file_path.replace("\\", "/") # Force Forward Slash
                    zipf.write(file_path, arcname)
                    print(f"Added: {arcname}")
                    
        if extra_files:
            for f in extra_files:
                if os.path.exists(f):
                    zipf.write(f, os.path.basename(f))
                    print(f"Added: {f}")

if __name__ == "__main__":
    folders = ['asr_trading', 'scripts', 'tests']
    files = ['main.py', 'requirements.txt', '.env']
    create_linux_zip(folders, 'package_linux.zip', files)
    print("Created package_linux.zip")
