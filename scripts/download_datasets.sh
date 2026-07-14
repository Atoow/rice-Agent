#!/bin/bash
# =========================================================
# 水稻病虫害数据集下载脚本
# 在你的电脑上运行这个脚本
# 前提: pip install kaggle
#       kaggle API token 放在 ~/.kaggle/kaggle.json
# =========================================================

echo "🌾 水稻病虫害数据集下载"
echo ""

# 1. Paddy Disease Classification (10,407 images, 10 classes)
echo "📥 [1/2] Paddy Disease Classification (10,407 images)"
kaggle competitions download -c paddy-disease-classification -p data/paddy_dataset
unzip -q data/paddy_dataset/paddy-disease-classification.zip -d data/paddy_dataset/
echo "  ✅ Done"

# 2. Rice Leaf Disease Dataset (7,284 images, 10 classes)
echo ""
echo "📥 [2/2] Rice Leaf Disease Dataset (7,284 images)"
kaggle datasets download -d shivas86/rice-leaf-disease-dataset -p data/rice_leaf_disease
unzip -q data/rice_leaf_disease/rice-leaf-disease-dataset.zip -d data/rice_leaf_disease/
echo "  ✅ Done"

echo ""
echo "🎉 全部下载完成！"
echo "   data/paddy_dataset/   - 10,407 张水稻病害图片 (10类)"
echo "   data/rice_leaf_disease/ - 7,284 张水稻叶片病害图片 (10类)"
