#!/usr/bin/env python3
# Файл: collect_listings.py
# Скрипт собирает в all_listings.txt содержимое всех .py-файлов проекта (рекурсивно).

import os
import sys

def collect_listings(root_dir: str, output_file: str):
    with open(output_file, "w", encoding="utf-8") as out:
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Пропускаем виртуальные окружения и кеши
            if any(part.startswith(".") or part in ("venv", "__pycache__") for part in dirpath.split(os.sep)):
                continue

            for fname in filenames:
                if fname.endswith(".py"):
                    full_path = os.path.join(dirpath, fname)
                    rel_path = os.path.relpath(full_path, root_dir)
                    out.write(f"\n--- {rel_path} ---\n")
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            out.write(f.read())
                    except Exception as e:
                        out.write(f"[Ошибка при чтении файла: {e}]\n")

if __name__ == "__main__":
    # Определяем корневую папку (где находится этот скрипт) и имя выходного файла
    project_root = os.path.dirname(os.path.abspath(__file__))
    output_txt = os.path.join(project_root, "all_listings.txt")

    collect_listings(project_root, output_txt)
    print(f"Списки файлов собраны в {output_txt}")
