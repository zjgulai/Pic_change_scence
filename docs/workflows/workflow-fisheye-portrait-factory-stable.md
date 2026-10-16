---
title: 180° 鱼眼动态抓拍重绘工厂工作流规范
doc_type: workflow
module: portrait
topic: fisheye-portrait-factory
status: stable
created: 2026-10-16
updated: 2026-10-16
owner: self
source: human+ai
---

# 180° 鱼眼动态抓拍重绘工厂工作流规范

## 1. 工作流定位

将任意静态人像参考图（默认基准：`assets/images/portrait-source-reference-stable.png`）转化为 **3:4 竖版、180° 超广角鱼眼强制透视、前景动态爆发 + 真实情绪抓拍** 系列成片的可复用流水线。

提供两套执行入口：
1. **Python CLI 批处理流水线**：`scripts/fisheye_portrait_pipeline.py`（基于 `configs/portrait-fisheye-themes-stable.json` 配置驱动，直接连接本地 Magpie MCP Image 异步并发出图）。
2. **Claude Code 多智能体编排工作流**：`.claude/workflows/fisheye-portrait-factory.js`（负责从新参考图视觉特征提取、新主题创意泛化、对抗性校验到调用 CLI 出图的全链路自动化）。

---

## 2. 四阶段流水线（Stage & Gate）

| 阶段 | 输入 | 核心职责 | 准出闸口（Verification Gate） |
| :--- | :--- | :--- | :--- |
| **Stage 1: Analyze（原图锚定）** | 原始人像 `assets/images/portrait-source-reference-stable.png` | 提取不可变视觉锚点：五官脸型、发色发型、服装款式、核心配饰（如土星珍珠项链）、环境光影（如冷蓝薄纱与右上蝴蝶投影） | 禁止使用“自动识别原图”类空泛元指令，必须输出具象可验证的视觉特征清单 |
| **Stage 2: Design（主题泛化）** | 视觉锚点清单 + 创意方向 | 构建 180° 鱼眼斜俯拍空间关系、超近景互动道具、高速闪光流体/粒子轨迹与自然抓拍表情（生成中英双语 Prompt） | 满足近景夸张放大、中景人脸居中低畸变、远景散景三层空间结构 |
| **Stage 3: Verify（对抗校验）** | 候选双语 Prompt | 检查身份锁定是否置顶、手部解剖学是否显式约束（1人、≤2臂、每手5指）、是否规避上游安全分类器敏感词组合 | 消除肢体冗余风险与安全误报词，输出定稿 `refinedEnglishPrompt` |
| **Stage 4: Generate（并发出图与核验）** | 定稿 Prompt + 参考图路径 | 通过 `scripts/fisheye_portrait_pipeline.py` 维持持久化 stdio 会话，调用 `magpie mcp image` (`codex/gpt-image-2`) 并轮询 `generation_result` 直至落盘 | 文件成功写入 `assets/images/portrait-edit-fisheye-<slug>-stable.png` 且通过视觉读取核验 |

---

## 3. CLI 工作流脚本使用指南

### 3.1 查看已配置的主题矩阵与生成状态

```bash
python3 scripts/fisheye_portrait_pipeline.py --list-themes
```

### 3.2 按主题编号或代号生成（支持单张或并发批量）

```bash
# 生成指定主题（若目标文件已存在默认跳过，加 --force 强制重绘）
python3 scripts/fisheye_portrait_pipeline.py --themes splash,bubble-barrage --force

# 并发生成全部预置主题
python3 scripts/fisheye_portrait_pipeline.py --themes all --concurrency 4 --force
```

### 3.3 传入自定义新主题或切换新人物参考图一键生成

```bash
python3 scripts/fisheye_portrait_pipeline.py \
  --ref assets/images/portrait-source-reference-stable.png \
  --custom-slug matcha-splash \
  --custom-prompt "Keep the exact subject identity, hairstyle, pale ice-blue dress, and pearl Saturn necklace from the reference image unchanged..." \
  --size 3:4
```

---

## 4. Claude Code 多智能体工作流调用方式

在 Claude Code 会话中，可直接调用 `.claude/workflows/fisheye-portrait-factory.js` 扩展新主题并自动生成图片：

```json
{
  "name": "fisheye-portrait-factory",
  "args": {
    "referenceImage": "assets/images/portrait-source-reference-stable.png",
    "generate": true,
    "themes": [
      {
        "slug": "snowglobe-burst",
        "title": "水晶雪花球爆裂瞬间",
        "concept": "Foreground crystal snowglobe cracking open with swirling silver snowflakes and water droplets toward the 180-degree fisheye lens while the girl laughs and winks."
      }
    ]
  }
}
```
