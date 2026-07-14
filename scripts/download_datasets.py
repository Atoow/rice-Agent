#!/usr/bin/env python
"""
水稻病虫害数据集下载脚本 (需要 Kaggle API)
在你的电脑上运行: python scripts/download_datasets.py

前提:
  pip install kaggle
  kaggle API token 放在 ~/.kaggle/kaggle.json (Linux/Mac)
  或 %USERPROFILE%\.kaggle\kaggle.json (Windows)
"""
import os, zipfile, subprocess, sys

DATASETS = {
    "paddy": {
        "name": "Paddy Disease Classification",
        "cmd": "kaggle competitions download -c paddy-disease-classification",
        "path": "data/paddy_dataset",
        "images": 10407,
        "classes": 10,
    },
    "rice_leaf": {
        "name": "Rice Leaf Disease Dataset",
        "cmd": "kaggle datasets download -d shivas86/rice-leaf-disease-dataset",
        "path": "data/rice_leaf_disease",
        "images": 7284,
        "classes": 10,
    },
}

def download(ds_id):
    info = DATASETS[ds_id]
    print(f"\n📥 {info['name']} ({info['images']:,} images, {info['classes']} classes)")
    
    os.makedirs(info["path"], exist_ok=True)
    result = subprocess.run(info["cmd"] + f" -p {info['path']}", 
                          shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  ❌ Failed: {result.stderr}")
        return False
    
    # Find and extract zip
    for f in os.listdir(info["path"]):
        if f.endswith('.zip'):
            zip_path = os.path.join(info["path"], f)
            print(f"  解压 {f}...")
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(info["path"])
            os.remove(zip_path)
            break
    
    # Count images
    count = 0
    for root, _, files in os.walk(info["path"]):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                count += 1
    print(f"  ✅ {count} 张图片")
    return True

if __name__ == "__main__":
    print("🌾 水稻病虫害数据集下载")
    print("="*50)
    
    for ds_id in DATASETS:
        download(ds_id)
    
    print(f"\n🎉 完成！")
    print("   data/paddy_dataset/     - 水稻病害图片 (10类)")
    print("   data/rice_leaf_disease/  - 水稻叶片病害图片 (10类)")
