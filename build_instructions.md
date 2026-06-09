# PyInstaller 打包指南

将 `mm_mil_converter.py` 打包为单个 `.exe` 文件。

---

## 方案 A：GitHub Actions 自动打包（推荐，Mac 上也能产出 .exe）

代码推送到 GitHub 后，CI 自动在 **Windows 虚拟机** 上打包，下载制品即可。

### 1. 推送代码到 GitHub

```bash
# 方式一：用 gh CLI
brew install gh
gh auth login
gh repo create mm-mil-converter --public --source=. --push

# 方式二：手动
# 在 github.com 上新建仓库，然后：
git remote add origin https://github.com/你的用户名/mm-mil-converter.git
git add -A
git commit -m "初始版本：mm ↔ mil 转换器"
git push -u origin main
```

### 2. CI 自动打包

推送后，GitHub Actions 自动启动打包流程。打开：
`https://github.com/你的用户名/mm-mil-converter/actions`

找到 **Build Windows EXE** 运行，点击进去 → **Artifacts** → 下载 `mm-mil-converter.exe`。

### 3. 手动触发

也可以在 Actions 页面手动触发：点击 **Build Windows EXE** → **Run workflow** → 选择分支 → **Run workflow**。

工作流文件见 [.github/workflows/build-exe.yml](.github/workflows/build-exe.yml)。

---

## 方案 B：Windows 本机打包

如果手头有 Windows 电脑。

```powershell
# 创建干净的虚拟环境（强烈推荐，减少打包体积）
python -m venv .venv
.venv\Scripts\activate

# 安装必要依赖
pip install pyqt6 pyinstaller
```

## 2. 打包命令

### 基础打包（推荐）

```powershell
pyinstaller --onefile --windowed --name "mm-mil-converter" mm_mil_converter.py
```

### 精简打包（体积更小）

```powershell
pyinstaller --onefile --windowed --name "mm-mil-converter" ^
    --exclude-module unittest ^
    --exclude-module email ^
    --exclude-module http ^
    --exclude-module xmlrpc ^
    --exclude-module pydoc ^
    --exclude-module distutils ^
    --exclude-module test ^
    mm_mil_converter.py
```

### UPX 压缩（进一步缩小）

1. 从 https://upx.github.io/ 下载 UPX
2. 解压后，打包时指定路径：

```powershell
pyinstaller --onefile --windowed --name "mm-mil-converter" ^
    --upx-dir "C:\tools\upx" ^
    mm_mil_converter.py
```

## 3. 输出位置

打包完成后，`.exe` 文件在：

```
dist\mm-mil-converter.exe
```

## 4. 体积参考

| 方案 | 约大小 |
|------|--------|
| 基础 onefile | ~45 MB |
| + 排除无用模块 | ~38 MB |
| + UPX 压缩 | ~28 MB |

> PyQt6 自带约 40MB+ 的 Qt 库，这是体积的主要来源。若需进一步缩减，可考虑 PySide6-Essentials 或改用系统自带 WebView 方案。

## 5. 常见问题

**Q: 启动报错 `No module named 'PyQt6.Qt6'`？**
```powershell
pyinstaller --onefile --windowed --name "mm-mil-converter" ^
    --hidden-import PyQt6.QtCore ^
    --hidden-import PyQt6.QtGui ^
    --hidden-import PyQt6.QtWidgets ^
    mm_mil_converter.py
```

**Q: 想隐藏控制台窗口？**
已使用 `--windowed`（即 `--noconsole`），双击运行不会弹出黑框。

**Q: 图标自定义？**
```powershell
pyinstaller --onefile --windowed --name "mm-mil-converter" ^
    --icon "app.ico" ^
    mm_mil_converter.py
```
