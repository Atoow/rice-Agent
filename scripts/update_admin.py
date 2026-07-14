import os

base = '/sessions/wonderful-happy-cannon/mnt/rice-agent/frontend'

with open(os.path.join(base, 'admin.html'), 'r', encoding='utf-8') as f:
    admin = f.read()

# Add batch upload CSS
admin = admin.replace(
    '.status.info { background: #e3f2fd; color: #1565c0; display: block; }',
    '.status.info { background: #e3f2fd; color: #1565c0; display: block; }\n.upload-batch { margin-top: 12px; }\n.upload-batch button { background: #1565c0; color: white; border: none; padding: 10px 28px; border-radius: 8px; font-size: 14px; cursor: pointer; }\n.upload-batch button:hover { background: #0d47a1; }\n.upload-batch button:disabled { background: #aaa; cursor: not-allowed; }'
)

# Add batch upload HTML section
admin = admin.replace(
    '<div class="status" id="status"></div>\n</div>',
    '<div class="status" id="status"></div>\n<div class="upload-batch" style="margin-top:16px;padding-top:14px;border-top:1px solid #eee;">\n<p style="font-size:13px;color:#888;margin-bottom:10px;">📂 批量导入文件夹（选择含 .txt .md .pdf 的目录）</p>\n<input type="file" id="folderInput" webkitdirectory directory multiple onchange="onFolderSelected(event)" style="display:none;">\n<button id="batchBtn" onclick="document.getElementById(\'folderInput\').click()" style="background:#1565c0;color:white;border:none;padding:10px 28px;border-radius:8px;font-size:14px;cursor:pointer;">选择文件夹</button>\n<span id="folderSelected" style="margin-left:12px;font-size:13px;color:#555;"></span>\n<button id="batchUploadBtn" onclick="batchUpload()" style="background:#2d6a1e;color:white;border:none;padding:10px 28px;border-radius:8px;font-size:14px;cursor:pointer;margin-left:8px;display:none;">导入全部</button>\n<div id="batchProgress" style="margin-top:8px;font-size:12px;color:#888;"></div>\n</div>\n</div>'
)

# Add batchUpload function
admin = admin.replace(
    'loadStats();',
    'let batchFiles = [];\nfunction onFolderSelected(e) {\nbatchFiles = Array.from(e.target.files).filter(f => /\\.(txt|md|pdf)$/i.test(f.name));\ndocument.getElementById(\'folderSelected\').textContent = \'chosen \' + batchFiles.length + \' files\';\ndocument.getElementById(\'batchUploadBtn\').style.display = batchFiles.length ? \'inline-block\' : \'none\';\n}\nasync function batchUpload() {\nif (!batchFiles.length) return;\nconst btn = document.getElementById(\'batchUploadBtn\');\nconst progress = document.getElementById(\'batchProgress\');\nbtn.disabled = true;\nlet ok = 0, fail = 0;\nfor (let i = 0; i < batchFiles.length; i++) {\nprogress.textContent = \'Importing: \' + (i+1) + \'/\' + batchFiles.length + \' - \' + batchFiles[i].name;\nconst form = new FormData();\nform.append(\'file\', batchFiles[i]);\ntry {\nconst res = await fetch(\'/admin/upload\', { method: \'POST\', body: form });\nconst data = await res.json();\nif (data.status === \'ok\') ok++; else fail++;\n} catch(e) { fail++; }\n}\nprogress.textContent = \'Done: \' + ok + \' ok, \' + fail + \' failed\';\nloadStats();\nbtn.disabled = false;\nbatchFiles = [];\ndocument.getElementById(\'folderSelected\').textContent = \'\';\ndocument.getElementById(\'batchUploadBtn\').style.display = \'none\';\n}\nloadStats();'
)

with open(os.path.join(base, 'admin.html'), 'w', encoding='utf-8') as f:
    f.write(admin)

print('admin.html updated')
