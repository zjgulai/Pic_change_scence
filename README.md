---
title: Pic_ZYT 180° 鱼眼动态抓拍重绘项目总览
doc_type: architecture
module: portrait
topic: project-overview
status: stable
created: 2026-10-16
updated: 2026-10-16
owner: self
source: human+ai
---

# Pic_ZYT — 180° 超广角鱼眼动态抓拍重绘项目

将静态人像照片转化为极具视觉冲击力、真实自然、富有幽默感的 **180° 超广角鱼眼高速闪光抓拍** 系列资产与自动化工作流项目。

---

## 1. 标准目录结构与资产导航

```text
Pic_ZYT/
├─ README.md                                                     # 项目入口与资产导航
├─ .claude/
│  └─ workflows/
│     └─ fisheye-portrait-factory.js                             # Claude Code 原生四阶段多智能体编排工作流
├─ assets/
│  └─ images/
│     ├─ portrait-source-reference-stable.png                    # [基准原图] 蓝纱蝴蝶光影影棚女性人像 (1086x1448, 3:4)
│     ├─ portrait-edit-fisheye-splash-stable.png                 # [主题 01] 冰饮爆裂飞溅瞬间
│     ├─ portrait-edit-fisheye-bubble-barrage-stable.png         # [主题 02] 梦幻虹光泡泡暴走瞬间
│     ├─ portrait-edit-fisheye-cake-smash-stable.png             # [主题 03] 仙气纱幕下的生日蛋糕偷吃抓包
│     ├─ portrait-edit-fisheye-confetti-pop-stable.png           # [主题 04] 冰晶银蓝蝴蝶礼炮炸裂瞬间
│     └─ portrait-edit-fisheye-konbini-freezer-stable.png        # [主题 05] 深夜便利店冰柜前的波子汽水喷发抓拍
├─ configs/
│  └─ portrait-fisheye-themes-stable.json                        # 结构化主题配置、原图视觉锚点与中英双语 Prompt 库
├─ scripts/
│  └─ fisheye_portrait_pipeline.py                               # Python 3.12+ 鱼眼抓拍批量生成与异步轮询 CLI 引擎
└─ docs/
   ├─ workflows/
   │  ├─ workflow-fisheye-portrait-factory-stable.md             # 鱼眼动态抓拍重绘工厂工作流规范
   │  └─ portrait-prompt-fisheye-splash-stable.md                # 5 大鱼眼抓拍主题矩阵与中英双语 Prompt 规范
   └─ knowledge/
      └─ knowledge-fisheye-prompt-engineering-stable.md          # 鱼眼提示词工程、Magpie 路由协议与安全误报排障知识库
```

---

## 2. 快速开始

### 2.1 查看所有主题状态

```bash
python3 scripts/fisheye_portrait_pipeline.py --list-themes
```

### 2.2 批量或按需重新生成预置主题

```bash
# 仅生成缺失主题
python3 scripts/fisheye_portrait_pipeline.py --themes all

# 强制重新生成指定主题
python3 scripts/fisheye_portrait_pipeline.py --themes splash,cake-smash --force
```

### 2.3 扩展自定义新主题一键出图

```bash
python3 scripts/fisheye_portrait_pipeline.py \
  --ref assets/images/portrait-source-reference-stable.png \
  --custom-slug NewThemeSlug \
  --custom-prompt "<English Prompt>" \
  --size 3:4
```
