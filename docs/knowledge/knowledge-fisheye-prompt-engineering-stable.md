---
title: 180° 鱼眼动态抓拍重绘提示词工程与排障知识库
doc_type: knowledge
module: portrait
topic: fisheye-prompt-engineering
status: stable
created: 2026-10-16
updated: 2026-10-16
owner: self
source: human+ai
---

# 180° 鱼眼动态抓拍重绘提示词工程与排障知识库

## 1. 本地生图路由与协议事实（`[事实]`）

1. **对话模型与生图通道分离**
   - `[事实]` 本地网关（`http://127.0.0.1:3425`，由 `/Applications/magpie.app/Contents/MacOS/magpie` 提供）中，文本对话模型 `vod/gemini-4-argon` 在 `/v1/images/generations` 端点仅返回文本（报错 `gemini-4-argon drew nothing`），不具备直接图像二进制输出能力。
   - `[事实]` Magpie 内置了专用图像/视频生成 MCP 服务（`/Applications/magpie.app/Contents/MacOS/magpie mcp image`），底层路由至已登录的 `codex/gpt-image-2`，原生支持传入本地文件数组 `reference_images` 进行高保真图生图编辑。
2. **持久化 stdio 异步轮询机制**
   - `[事实]` `magpie mcp image` 的 `generate_image` 工具在约 20 秒内未完成时会返回异步任务 ID（如 `image-89594-1`），且该任务生命周期绑定在当前 `magpie mcp image` 子进程内存中。若调用方提前关闭 `stdin` 或终止子进程，生成任务即中断。
   - **解决方案**：必须在同一个持久化 `stdio` 子进程中循环发送 `generation_result` JSON-RPC 请求（已封装于 `scripts/fisheye_portrait_pipeline.py`），约 40～80 秒即可完成落盘。
3. **画幅比例与实际输出分辨率**
   - `[事实]` 原始参考图 `assets/images/portrait-source-reference-stable.png` 分辨率为 `1086×1448`（精确 `3:4` 竖幅）。虽然 `gpt-image-2` 文档将固定枚举尺寸写作 `1024x1536`（2:3），但在传入 `3:4` 参考图的编辑模式下，全部 5 张生成成片的实际落盘分辨率均为 `1086×1448`（严格保持 `3:4` 竖幅）。

---

## 2. 图生图提示词构造经验（`[推断]`）

1. **具象视觉锚点优于元指令（Meta-Instructions）**
   - `[推断]` 诸如“自动识别人物数量、五官、发型、服装、拍摄地点”的描述属于面向人类的元指令；在图生图模型中，将其转化为显式前置特征锚点（`Single young East Asian woman, dark-brown wavy half-up hair with airy bangs, pale ice-blue spaghetti-strap dress, white pearl necklace with silver Saturn orb pendant, sheer blue organza drapes, upper-right butterfly-wing light projection`）能显著提升跨动作重绘时的配饰与光影保留率。
2. **手部与肢体解剖学显式定量约束**
   - `[推断]` 在 180° 鱼眼超近景强制透视下，前景大幅放大的手持道具容易诱发多手或指节融合。在 Prompt 中显式声明 `Exactly one person, no more than two arms and two five-fingered hands` 后，实测生成的 5 张鱼眼抓拍成片均未出现多余手臂或六指畸变。
3. **180° 鱼眼透视与黑框边界说明**
   - `[事实]` 尽管在 Prompt 中写入了 `subtle natural optical circular vignetting, never a pasted-on black ring`，`codex/gpt-image-2` 在响应“180-degree fisheye lens”词条时，仍在成片四角渲染了明显的圆形鱼眼镜筒黑边。
   - `[推断]` 若后续需要完全无四角黑边的满画幅超广角变形，应将镜头词从 `180-degree fisheye lens` 调整为 `ultra-wide 12mm rectilinear/diagonal rectilinear-fisheye lens filling the entire rectangular frame with zero corner vignette`。

---

## 3. 安全分类器误报排障记录

- **`[事实]` 拦截记录**：在生成主题 05（深夜便利店冰柜场景）首版时，上游返回 `400 Bad Request: Your request was rejected by the safety system... safety_violations=[sexual]`（Request ID: `a0a585af-7dd5-4c3e-a485-9b8cacaca9e9`）。
- **`[推断]` 触发成因与规避方案**：首版 Prompt 同时包含了 `spaghetti-strap dress`（细肩带裙）、`open ice-cream chest`（敞口冷柜，其中 `chest` 具有胸部双关义）、`angled slightly upward toward her face`、`She leans into...` 及 `curling around a sea-salt-blue ice pop`（冰棒）。将场景改为 `glowing cool-blue glass-door refrigerator`（玻璃门冷柜）与 `chilled glass bottle of sparkling blue ramune soda`（波子汽水玻璃瓶）并采用斜俯拍视角后，一次通过安全审查并成功出图。
