Excellent clarification! Here’s a comprehensive, expert-level prompt for O3 in Windsurf that will ensure your code review checks for all these requirements:

**Prompt for O3 Code Review (Usage Function & Compliance Focus):**

> Please perform a detailed code review of the following script(s) with a focus on compliance with our project standards:
>
> **For each script file:**
> 1. **File Description:**  
>    - Check that there is a concise, informative description at the top of the file.
>    - Ensure the description helps an agent (or human reviewer) understand the script’s purpose.
>    - The description must include:  
>      - All relevant third-party documentation links  
>      - Expected input(s)  
>      - Expected output(s)
>
> 2. **Usage Function:**  
>    - Confirm there is a usage function that demonstrates the script’s core functionality (not just import checks).
>    - The usage function must be called within the `if __name__ == "__main__":` block.
>    - The usage function should clearly show how to use the script, what input it expects, and what output is reasonable.
>    - The usage function must verify the core logic of the script, not just that it runs or imports.
>
> 3. **Validation:**  
>    - Ensure the usage function compares expected and actual results in a meaningful way.
>    - The usage must not be superficial (e.g., only testing imports or printing a static string).
>
> 4. **Documentation and Clarity:**  
>    - Highlight any missing, unclear, or insufficient documentation or usage examples.
>    - Suggest improvements if the description, documentation links, or usage function are missing or inadequate.
>
> **Do not generate traditional test cases or boilerplate. Focus on reviewing and critiquing the above aspects only.**
>
> Here is the code:
> [PASTE CODE HERE]

### Why this prompt is effective:

- **Explicitly checks for all your standards**: description, documentation, expected input/output, and a meaningful usage function.
- **Prevents superficial checks**: makes it clear that import-only “usage” is not acceptable.
- **Agent-friendly**: ensures the script is easy for both humans and AI agents to understand, run, and validate.
- **Actionable feedback**: instructs O3 to highlight and suggest improvements for any deficiencies.

**Tip:**  
You can copy and paste this prompt into Windsurf’s Cascade chat with O3 selected, and paste your script(s) below it. This will guide O3 to deliver a focused, standards-based review tailored to your workflow.