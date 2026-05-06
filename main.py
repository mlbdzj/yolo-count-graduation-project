import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("KPI Monitor")

    # Paths
    base_dir = Path(__file__).parent
    config_path = base_dir / "config.yaml"
    model_path = base_dir / "best.pt"

    if not model_path.exists():
        print(f"[WARN] 模型文件未找到: {model_path}")

    window = MainWindow(str(config_path), str(model_path))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
