````markdown
# Gemini CLI Stress Test Harness

This Python tool benchmarks the response time and reliability of the Google Gemini CLI on complex or large prompts, supporting concurrent execution for load testing.

---

## Features

- **Concurrent execution:** Run multiple parallel Gemini CLI jobs.
- **Prompt file support:** Load any `.md` or `.txt` prompt from disk.
- **Smart progress bar:** See task progress in real time via `tqdm`.
- **Adaptive or static timeout:** Baseline a single run or set a static timeout.
- **Saves every output:** Output, error, and a machine-readable JSON report per test run.
- **Flexible input:** Send prompt as a CLI arg (`-p ...`) or via stdin (file/pipe), based on CLI command.
- **Extensive logging:** Uses `loguru` for rich log output.

---

## Usage

### Standard timeout

```
python gemini_stress_test.py --concurrent-runs 5 --timeout 120 --cmd "gemini -y -p" --prompt-file prompt.md
```

### Adaptive timeout (auto-computes best timeout)

```
python gemini_stress_test.py --concurrent-runs 5 --cmd "gemini -y -p" --prompt-file prompt.md
```

### With stdin piping (for long/complex prompts)

```
python gemini_stress_test.py --concurrent-runs 5 --cmd "gemini -y" --prompt-file prompt.md
```

> **Note:** To use stdin mode, ensure your script is configured to send the prompt file to Gemini’s stdin instead of via the `-p` argument (recommended for large or complex prompts).

---

## Output

All logs, `stdout`, `stderr`, and a single `report.json` are saved to a new timestamped folder for each run:

```
./test_run_YYYYMMDD_HHMMSS/
```

---

## Gemini CLI Input Recommendations

- **`-p ""`**: Use for small/medium prompts; passed as an argument.
- **stdin (`gemini -y < prompt.md`)**: Use for large/complex prompts or automated chaining.
    - Only one mode is supported at a time ([Gemini CLI docs](https://cloud.google.com/gemini/docs/codeassist/gemini-cli); [issue #4405](https://github.com/google-gemini/gemini-cli/issues/4405)).
    - Don’t use both `-p` and stdin; if both are supplied, only `-p` is used, and stdin is ignored.

---

## System Requirements

- Python 3.8+
- [`loguru`](https://pypi.org/project/loguru/)
- [`tqdm`](https://pypi.org/project/tqdm/)
- [`typer`](https://pypi.org/project/typer/)
- [Gemini CLI](https://cloud.google.com/gemini/docs/codeassist/gemini-cli) installed and authenticated

---

## Example Prompt File (`prompt.md`)

```
You are a skilled AI project architect.

Your task is to simulate an entire year-long global product launch plan.

In this simulation, there are:
- 6 regional offices (North America, Europe, Asia, South America, Africa, Australia)
- 20 cross-functional stakeholders (execs, engineers, designers, sales, support)
- 50 unique product features launching across multiple timelines

Instructions:
1. Break down the plan into 4 quarters (Q1 to Q4).
2. For each quarter, define 3–5 major milestones.
3. For each milestone, define:
   - A short description
   - Start and end dates
   - Assigned leads
   - Dependencies and region(s) affected
   - Estimated effort in person-weeks

4. After establishing the quarterly plans:
   - Generate a matrix of responsibility showing which stakeholders are involved in which milestones.
   - Include a JSON summary for each regional office with aggregated effort, milestones owned, and feature coverage.

5. Return the ENTIRE OUTPUT as formatted JSON using the schema below (truncate only if absolutely necessary).

JSON Schema:
{
  "quarters": [
    {
      "quarter": "Q1",
      "milestones": [
        {
          "title": "Launch Alpha",
          "description": "Initial Alpha release with testing cohort",
          "start_date": "2025-01-15",
          "end_date": "2025-02-28",
          "assigned_leads": ["Alice", "David"],
          "regions": ["North America"],
          "effort_person_weeks": 120
        }
      ]
    }
  ],
  "responsibility_matrix": { "Alice": ["Q1: Launch Alpha", "Q2: Beta Sprint"] },
  "regional_summaries": {
    "North America": {
      "milestones": 8,
      "total_effort": 460,
      "features_covered": ["Feature A", "Feature D", "..."]
    }
  }
}

When responding, begin generating data as quickly as possible.
If the whole output is too large for the context window, begin with Q1 and stream the remainder.
Do not include any explanatory text — only return the JSON object.
```

---

## References

- [Gemini CLI Documentation](https://cloud.google.com/gemini/docs/codeassist/gemini-cli)
- [How to pipe prompts via stdin](https://github.com/google-gemini/gemini-cli/issues/4405)
- [Official blog: Google announces Gemini CLI](https://blog.google/technology/developers/introducing-gemini-cli-open-source-ai-agent/)
- [DataCamp: Gemini CLI Guide](https://www.datacamp.com/tutorial/gemini-cli)
- [Practical Guide on Dev.to](https://dev.to/shahidkhans/a-practical-guide-to-gemini-cli-941)
- [YouTube: Gemini CLI for Testing & Automation](https://www.youtube.com/watch?v=hsAYuKHVQhk)

---

**Current date:** Friday, July 18, 2025, 4:16 PM EDT

```

[1] https://www.datacamp.com/tutorial/gemini-cli
[2] https://www.youtube.com/watch?v=fzA9OZy0TY0
[3] https://blog.google/technology/developers/introducing-gemini-cli-open-source-ai-agent/
[4] https://cloud.google.com/gemini/docs/codeassist/gemini-cli
[5] https://dev.to/shahidkhans/a-practical-guide-to-gemini-cli-941
[6] https://www.youtube.com/watch?v=hsAYuKHVQhk
[7] https://www.youtube.com/watch?v=MHmtBM1kFrg
[8] https://thecreatorsai.com/p/complete-guide-to-gemini-cli
[9] https://www.reddit.com/r/GeminiAI/comments/1lkojt8/gemini_cli_a_comprehensive_guide_to_understanding/
[10] https://blog.logrocket.com/gemini-cli-tutorial/