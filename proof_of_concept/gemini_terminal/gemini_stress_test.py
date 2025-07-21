"""
###  How to Use with Gemini CLI
```zsh
gemini -y < prompt.md
```

### Or with your Python benchmarking script:
```zsh
python gemini_stress_test.py --cmd "gemini -y" --prompt-file prompt.md```

### Stress Testing with Concurrency
```zsh
python gemini_stress_test.py --concurrent-runs 5 --timeout 120 --cmd "gemini -y" --prompt-file prompt.md
```
"""

import os
import math
import json
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Optional

import typer
from loguru import logger
from tqdm import tqdm

app = typer.Typer(help="Stress test Gemini CLI with concurrent prompt executions.")


# --- Async Helpers ---

async def save_stream_to_file(stream: asyncio.StreamReader, filepath: str):
    with open(filepath, "wb") as f:
        while True:
            line = await stream.readline()
            if not line:
                break
            f.write(line)


async def run_single_test(
    test_id: int,
    prompt: str,
    command: List[str],
    timeout: int,
    embed_stdout: bool,
    output_dir: str
) -> Dict[str, Any]:
    start_time = datetime.now(timezone.utc)
    log_prefix = f"[Test-{test_id:02d}]"

    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    run_id_str = f"run{test_id:02d}"
    stdout_file = os.path.join(output_dir, f"output_{timestamp}_{run_id_str}.json")
    stderr_file = os.path.join(output_dir, f"error_{timestamp}_{run_id_str}.log")

    result: Dict[str, Any] = {
        "test_id": test_id,
        "status": "UNKNOWN",
        "start_time_utc": start_time.isoformat(),
        "duration_seconds": -1.0,
        "exit_code": None,
        "stdout_path": stdout_file,
        "stderr_content": "",
    }

    full_command = command + [prompt]
    try:
        proc = await asyncio.create_subprocess_exec(
            *full_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await asyncio.wait_for(
            asyncio.gather(
                save_stream_to_file(proc.stdout, stdout_file),
                save_stream_to_file(proc.stderr, stderr_file),
                proc.wait()
            ),
            timeout=timeout
        )

        result["exit_code"] = proc.returncode
        if proc.returncode == 0:
            result["status"] = "SUCCESS"
            logger.success(f"{log_prefix} completed.")
        else:
            result["status"] = "FAILURE"
            logger.warning(f"{log_prefix} exited with code {proc.returncode}")

    except asyncio.TimeoutError:
        result["status"] = "TIMEOUT"
        logger.error(f"{log_prefix} timed out after {timeout} seconds.")
        proc.kill()
        await proc.wait()
    except FileNotFoundError:
        result["status"] = "FAILURE"
        result["stderr_content"] = f"ERROR: Command '{command[0]}' not found."
        logger.error(f"{log_prefix} {result['stderr_content']}")
    except Exception as e:
        result["status"] = "FAILURE"
        result["stderr_content"] = f"Exception occurred: {e}"
        logger.error(f"{log_prefix} {result['stderr_content']}")

    end_time = datetime.now(timezone.utc)
    result["duration_seconds"] = (end_time - start_time).total_seconds()

    try:
        with open(stderr_file, "r", encoding="utf-8") as f:
            result["stderr_content"] += f.read()
    except FileNotFoundError:
        pass

    if embed_stdout and result["status"] == "SUCCESS":
        try:
            with open(stdout_file, "r", encoding="utf-8") as f:
                result["stdout_content"] = f.read()
        except Exception as e:
            result["stdout_content"] = f"Error reading stdout: {e}"

    return result


# --- Main CLI ---

@app.command()
def run_stress_test(
    prompt_file: str = typer.Option("prompt.md", help="Path to prompt .md/.txt file."),
    cmd: str = typer.Option("gemini -y -p", "--cmd", help="Base command to run, with prompt appended"),
    concurrent_runs: int = typer.Option(1, "--concurrent-runs", "-c", help="Number of concurrent test executions."),
    timeout: Optional[int] = typer.Option(None, "--timeout", "-t", help="Fixed timeout in seconds."),
    adaptive_timeout_buffer: float = typer.Option(1.5, help="Timeout multiplier if using adaptive mode."),
    embed_stdout: bool = typer.Option(False, help="Include stdout contents in the JSON report.")
):
    """
    Run Gemini CLI concurrently for performance/load testing.
    """
    import sys

    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    prompt_path = os.path.abspath(prompt_file)

    if not os.path.exists(prompt_path):
        logger.error(f"Prompt file not found: {prompt_path}")
        raise typer.Exit(code=1)

    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt = f.read().strip()

    output_dir = os.path.join(script_dir, f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(output_dir, exist_ok=True)

    command_parts = cmd.strip().split()
    timeout_to_use = timeout

    async def orchestrate():
        nonlocal timeout_to_use

        if timeout is None:
            logger.info("Running baseline to determine adaptive timeout...")
            baseline = await run_single_test(0, prompt, command_parts, 600, False, output_dir)
            if baseline["status"] != "SUCCESS":
                logger.error("Baseline run failed. Cannot determine timeout.")
                return

            baseline_secs = baseline["duration_seconds"]
            timeout_to_use = int(math.ceil(baseline_secs * adaptive_timeout_buffer))
            logger.info(f"Baseline: {baseline_secs:.2f}s → timeout = {timeout_to_use}s")

        tasks = [
            run_single_test(i + 1, prompt, command_parts, timeout_to_use, embed_stdout, output_dir)
            for i in range(concurrent_runs)
        ]

        results = []
        with tqdm(total=concurrent_runs, desc="Running Tests") as pbar:
            for coro in asyncio.as_completed(tasks):
                result = await coro
                results.append(result)
                pbar.update(1)

        # Output final report
        summary = {
            "started": datetime.now(timezone.utc).isoformat(),
            "concurrent_runs": concurrent_runs,
            "timeout_seconds": timeout_to_use,
            "command": cmd,
            "prompt_file": prompt_file,
            "success": sum(1 for r in results if r["status"] == "SUCCESS"),
            "failures": sum(1 for r in results if r["status"] == "FAILURE"),
            "timeouts": sum(1 for r in results if r["status"] == "TIMEOUT"),
        }

        report = {
            "summary": summary,
            "results": sorted(results, key=lambda r: r["test_id"])
        }

        report_path = os.path.join(output_dir, "report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        logger.info(f"✅ Done. Results saved to: {report_path}")
        logger.info(f"✅ Success: {summary['success']} | ❌ Failures: {summary['failures']} | ⏱️ Timeouts: {summary['timeouts']}")

    asyncio.run(orchestrate())


if __name__ == "__main__":
    app()
