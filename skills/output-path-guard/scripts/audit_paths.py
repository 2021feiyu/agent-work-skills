# -*- coding: utf-8 -*-
"""产出物落盘路径审计（只读）。

用法:
    python audit_paths.py "<项目根目录>" [--home <用户目录>]

扫描项目内 .py/.js/.ts/.json/.yaml/.md/.ps1/.sh/.bat 文件中
可能把产出物写到用户桌面 / 用户目录 / C 盘的代码模式，按危险度分级输出。

本脚本不修改任何文件。
"""
import argparse
import os
import re
import sys

SCAN_EXT = {
    ".py", ".js", ".ts", ".mjs", ".cjs", ".json", ".yaml", ".yml",
    ".md", ".ps1", ".sh", ".bat", ".cmd",
}
SKIP_DIR_PARTS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "site-packages", "dist", "build", ".next",
}

# (等级, 名称, 正则)
RULES = [
    ("CRITICAL", "硬编码 C 盘用户路径",
     re.compile(r"C:[\\/]+Users[\\/]+[^\\/\"'\s]+[\\/]+(?:Desktop|Documents|Downloads)",
                re.IGNORECASE)),
    ("CRITICAL", 'expanduser("~") + Desktop',
     re.compile(r"expanduser\s*\(\s*['\"]~['\"]\s*\)\s*[^,;\n]{0,40}(Desktop|Documents|Downloads)",
                re.IGNORECASE)),
    ("CRITICAL", "~/Desktop 简写",
     re.compile(r"~/?(?:Desktop|Documents|Downloads)\b", re.IGNORECASE)),
    ("HIGH", 'expanduser("~") 直接拼输出',
     re.compile(r"expanduser\s*\(\s*['\"]~['\"]\s*\)")),
    ("MEDIUM", "SHGetFolderPath / KnownFolder 用户目录 API",
     re.compile(r"SHGetFolderPath|FOLDERID_Desktop|FOLDERID_Downloads", re.IGNORECASE)),
    ("MEDIUM", "Copy-Item / shutil 复制到桌面",
     re.compile(r"(Copy-Item|shutil\.copy\w*|copyFileSync)[^\n]{0,80}Desktop", re.IGNORECASE)),
    ("LOW", "提及 Desktop（可能是产品名或注释，需人工判断）",
     re.compile(r"Desktop|桌面")),
]

LEVEL_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def iter_files(root):
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIR_PARTS]
        for f in fn:
            if os.path.splitext(f)[1].lower() in SCAN_EXT:
                yield os.path.join(dp, f)


def audit_file(path, root, home):
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return []
    findings = []
    for i, line in enumerate(lines, 1):
        for level, name, pat in RULES:
            if pat.search(line):
                # 用户主目录已被参数化时降级（说明是跨机可移植写法，风险较低）
                lv = level
                if home and home.lower() in line.lower() and level == "LOW":
                    lv = "LOW"
                findings.append((lv, name, i, line.strip()))
                break  # 每行只报最高优先级规则
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="项目根目录")
    ap.add_argument("--home", default=os.path.expanduser("~"),
                    help="用户主目录（用于识别硬编码，默认当前用户）")
    ap.add_argument("--quiet", action="store_true", help="只输出 CRITICAL/HIGH")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print("ERROR: 目录不存在:", root)
        return 2

    total, by_level = 0, {}
    for path in iter_files(root):
        for level, name, lineno, snippet in audit_file(path, root, args.home):
            if args.quiet and level not in ("CRITICAL", "HIGH"):
                continue
            rel = os.path.relpath(path, root)
            print("[%-8s] %s:%d  (%s)" % (level, rel, lineno, name))
            print("           %s" % snippet[:160])
            total += 1
            by_level[level] = by_level.get(level, 0) + 1

    print("\n" + "=" * 60)
    if total == 0:
        print("未发现可疑路径引用 —— 通过")
    else:
        print("合计 %d 处命中:" % total)
        for lv in sorted(by_level, key=lambda x: LEVEL_ORDER[x]):
            print("   %-8s %d" % (lv, by_level[lv]))
        print("\n提醒:")
        print(" - CRITICAL/HIGH 必须修复（产出物不得写用户桌面/用户目录/C盘）")
        print(" - MEDIUM/LOW 需人工判断：只读资源查找（如字体目录）可放行，")
        print("   状态缓存建议挪进工作空间")
        print(" - 修复前先做全量备份，移动而非删除")

    # 顺带体检：用户桌面是否已存在本项目产出物
    desk = os.path.join(args.home, "Desktop")
    if os.path.isdir(desk):
        items = [x for x in os.listdir(desk)]
        if items:
            print("\n[体检] 用户桌面当前有 %d 项内容（需确认是否有本项目产出物）:" % len(items))
            for x in sorted(items)[:20]:
                print("   -", x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
