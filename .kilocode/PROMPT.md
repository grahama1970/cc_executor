### **Mandatory Final Step: Self-Correction and Verification**

Once you believe you have completed the primary coding task, you **MUST** perform a final quality check using the `kilocode-review` tool. This is a non-negotiable step to ensure your work adheres to all project constraints.

Follow this procedure exactly:

#### **1. Identify Changed Files**
Use your file system tools to create a list of all file paths you have created or modified during this task.

#### **2. Initiate Review**
Call the `kilocode-review.start_review` tool. Pass the file paths as a single space-separated string to the `files` argument.

*   **Example Call:**
    ```xml
    <execute_command>
      <tool_name>kilocode-review</tool_name>
      <function_name>start_review</function_name>
      <args>
        <files>src/path/to/file1.py src/path/to/another/file2.py</files>
      </args>
    </execute_command>
    ```
*   The tool will immediately return a JSON object containing a `review_id`. This ID is the path to the results directory. Save this `review_id`.

#### **3. Wait for Completion**
The review process is **asynchronous** and can take several minutes to run.

*   You must wait patiently. A good strategy is to wait for **2-3 minutes** before proceeding to the next step.

#### **4. Retrieve and Analyze Results**
After waiting, call the `kilocode-review.get_review_results` tool, passing the `review_id` you received in step 2.

*   **Example Call:**
    ```xml
    <execute_command>
      <tool_name>kilocode-review</tool_name>
      <function_name>get_review_results</function_name>
      <args>
        <review_id>docs/code_review/20231028_120000_abcdef123</review_id>
      </args>
    </execute_command>
    ```
*   This will return a JSON object containing the full review.
*   Carefully examine the content of the `results.actionable_fixes` field. This contains fixes that are pre-validated and safe to apply.
*   Also, review `results.incompatible_suggestions` to learn what standard fixes are incorrect for this project's context.

#### **5. Perform Self-Correction**
If the `results.actionable_fixes` field contains any suggestions, you are **REQUIRED** to open the relevant files and apply the changes exactly as described.

*   If `results.actionable_fixes` is empty or `null`, no corrections are needed.

#### **6. Conclude Task**
After applying all required fixes, you may consider the task complete. In your final message, explicitly state that you have finished the work and confirm that it has passed the automated contextual review.