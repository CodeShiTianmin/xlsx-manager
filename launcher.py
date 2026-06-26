"""PyInstaller 打包入口（顶层脚本，使用绝对导入）。

不能用 app/__main__.py 作为打包入口：它被当作顶层脚本执行时没有父包，
`from .gui import main` 会触发 "attempted relative import with no known parent package"。
"""

from app.gui import main

if __name__ == "__main__":
    main()
