#!/usr/bin/env python3
"""
180° 超广角鱼眼动态抓拍重绘工作流引擎 (Fisheye Portrait Action Pipeline).

之所以使用持久化 stdio 子进程驱动 `magpie mcp image`，是因为其内部异步生成任务与
stdio 会话生命周期绑定，单次短连接无法完成 >20s 的轮询。
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fisheye_pipeline")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "portrait-fisheye-themes-stable.json"
DEFAULT_MAGPIE_BIN = Path("/Applications/magpie.app/Contents/MacOS/magpie")
JOB_ID_PATTERN = re.compile(r'call generation_result with id "([^"]+)"')


@dataclass(frozen=True)
class GenerationTask:
    slug: str
    title: str
    prompt: str
    reference_image: Path
    output_path: Path
    size: str = "3:4"


@dataclass(frozen=True)
class GenerationOutcome:
    slug: str
    output_path: Path
    success: bool
    message: str


def load_theme_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    return json.loads(config_path.read_text(encoding="utf-8"))


def run_magpie_mcp_image(
    task: GenerationTask,
    magpie_bin: Path = DEFAULT_MAGPIE_BIN,
    timeout_sec: int = 300,
) -> GenerationOutcome:
    if not magpie_bin.exists():
        raise FileNotFoundError(f"未找到 Magpie 可执行文件: {magpie_bin}")
    if not task.reference_image.exists():
        raise FileNotFoundError(f"参考图不存在: {task.reference_image}")

    task.output_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("启动生成 [%s] -> %s", task.slug, task.output_path.relative_to(PROJECT_ROOT))

    proc = subprocess.Popen(
        [str(magpie_bin), "mcp", "image"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    try:
        assert proc.stdin is not None
        assert proc.stdout is not None

        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "fisheye-pipeline", "version": "1.0.0"},
            },
        }
        proc.stdin.write(json.dumps(init_req) + "\n")
        proc.stdin.flush()

        next_req_id = 2
        for raw_line in proc.stdout:
            line = raw_line.strip()
            if not line:
                continue
            msg = json.loads(line)

            if msg.get("id") == 1:
                proc.stdin.write(
                    json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
                )
                call_req = {
                    "jsonrpc": "2.0",
                    "id": next_req_id,
                    "method": "tools/call",
                    "params": {
                        "name": "generate_image",
                        "arguments": {
                            "prompt": task.prompt,
                            "reference_images": [str(task.reference_image.resolve())],
                            "path": str(task.output_path.resolve()),
                            "size": task.size,
                        },
                    },
                }
                next_req_id += 1
                proc.stdin.write(json.dumps(call_req) + "\n")
                proc.stdin.flush()
                continue

            if "error" in msg:
                err_msg = json.dumps(msg["error"], ensure_ascii=False)
                logger.error("[%s] JSON-RPC 错误: %s", task.slug, err_msg)
                return GenerationOutcome(task.slug, task.output_path, False, err_msg)

            result = msg.get("result", {})
            content_list = result.get("content", [])
            text = content_list[0].get("text", "") if content_list else ""

            if result.get("isError"):
                logger.error("[%s] 生成失败: %s", task.slug, text.strip())
                return GenerationOutcome(task.slug, task.output_path, False, text.strip())

            match = JOB_ID_PATTERN.search(text)
            if match:
                job_id = match.group(1)
                logger.info("[%s] 异步生成中 (job=%s)...", task.slug, job_id)
                poll_req = {
                    "jsonrpc": "2.0",
                    "id": next_req_id,
                    "method": "tools/call",
                    "params": {
                        "name": "generation_result",
                        "arguments": {"id": job_id},
                    },
                }
                next_req_id += 1
                proc.stdin.write(json.dumps(poll_req) + "\n")
                proc.stdin.flush()
            else:
                logger.info("[%s] 生成完成: %s", task.slug, text.strip().replace("\n", " "))
                return GenerationOutcome(task.slug, task.output_path, True, text.strip())

        return GenerationOutcome(task.slug, task.output_path, False, "MCP stdout 提前关闭")
    finally:
        proc.kill()
        proc.wait(timeout=5)


def build_tasks_from_args(args: argparse.Namespace, config: dict[str, Any]) -> list[GenerationTask]:
    ref_path = (
        Path(args.ref).resolve()
        if args.ref
        else (PROJECT_ROOT / config["default_reference_image"]).resolve()
    )
    size = args.size or config.get("default_size", "3:4")

    if args.custom_slug and args.custom_prompt:
        out_path = PROJECT_ROOT / "assets" / "images" / f"portrait-edit-fisheye-{args.custom_slug}-stable.png"
        return [
            GenerationTask(
                slug=args.custom_slug,
                title=f"Custom ({args.custom_slug})",
                prompt=args.custom_prompt,
                reference_image=ref_path,
                output_path=out_path,
                size=size,
            )
        ]

    themes = config.get("themes", [])
    selected_keys = [k.strip() for k in (args.themes or "").split(",") if k.strip()]
    if not selected_keys:
        raise ValueError("必须指定 --themes <slug1,slug2|all> 或 --custom-slug + --custom-prompt")

    tasks: list[GenerationTask] = []
    for item in themes:
        if "all" in selected_keys or item["slug"] in selected_keys or item["id"] in selected_keys:
            out_path = PROJECT_ROOT / item["output_file"]
            if out_path.exists() and not args.force:
                logger.info("跳过已存在的正式资产 [%s]: %s (使用 --force 强制重绘)", item["slug"], out_path.name)
                continue
            prompt = item["english_prompt"] if args.lang == "en" else item["chinese_prompt"]
            tasks.append(
                GenerationTask(
                    slug=item["slug"],
                    title=item["title"],
                    prompt=prompt,
                    reference_image=ref_path,
                    output_path=out_path,
                    size=size,
                )
            )
    return tasks


def list_themes(config: dict[str, Any]) -> None:
    ref = PROJECT_ROOT / config["default_reference_image"]
    print(f"默认参考图: {ref.relative_to(PROJECT_ROOT)} ({'已就绪' if ref.exists() else '缺失'})")
    print("-" * 88)
    print(f"{'ID':<4} {'Slug':<18} {'状态':<10} {'输出路径':<50}")
    print("-" * 88)
    for t in config.get("themes", []):
        out = PROJECT_ROOT / t["output_file"]
        status = "✅ 已生成" if out.exists() else "⏳ 未生成"
        print(f"{t['id']:<4} {t['slug']:<18} {status:<10} {t['output_file']}")
    print("-" * 88)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="180° 超广角鱼眼动态抓拍重绘工作流 CLI"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="主题配置文件路径",
    )
    parser.add_argument(
        "--list-themes",
        action="store_true",
        help="列出所有预置鱼眼抓拍主题及产物状态",
    )
    parser.add_argument(
        "--themes",
        type=str,
        help="要生成的主题 slug 或编号（逗号分隔，或传 all）",
    )
    parser.add_argument(
        "--ref",
        type=Path,
        help="覆盖默认参考人物图片路径",
    )
    parser.add_argument(
        "--lang",
        choices=["en", "zh"],
        default="en",
        help="使用英文还是中文 Prompt 执行生成 (默认: en)",
    )
    parser.add_argument(
        "--size",
        type=str,
        default="3:4",
        help="生成比例或尺寸 (默认: 3:4 竖版，对应原图比例输出 1086x1448)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="最大并发生成任务数 (默认: 4)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="即使目标图片已存在也强制重新生成",
    )
    parser.add_argument(
        "--custom-slug",
        type=str,
        help="自定义新主题的标识名 (如 matcha-splash)",
    )
    parser.add_argument(
        "--custom-prompt",
        type=str,
        help="自定义新主题的完整 Prompt",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_theme_config(args.config)

    if args.list_themes:
        list_themes(config)
        return 0

    tasks = build_tasks_from_args(args, config)
    if not tasks:
        logger.info("没有需要执行的生成任务。")
        return 0

    outcomes: list[GenerationOutcome] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
        future_map = {pool.submit(run_magpie_mcp_image, task): task for task in tasks}
        for future in concurrent.futures.as_completed(future_map):
            outcomes.append(future.result())

    failed = [o for o in outcomes if not o.success]
    if failed:
        for f in failed:
            logger.error("任务失败 [%s]: %s", f.slug, f.message)
        return 1

    logger.info("全部 %d 个鱼眼重绘任务已成功完成。", len(outcomes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
