Lesson 1: The Environment is Everything


  This was the most persistent and misleading theme of our entire investigation. We repeatedly suspected
  issues with API keys, configuration files, and command parsing, all of which are symptoms of the same
  root cause: a process's environment is its entire world, and the server's world is not your terminal's
  world.


   * The Trap We Fell Into: We assumed that because a command worked in our interactive Zsh, it should work
     when launched by Python. We forgot that the Python script, run by Uvicorn, inherits a sterile, minimal
     environment, lacking the paths, variables (ANTHROPIC_API_KEY), and working directory context of our
     shell.
   * The Enduring Principle: Never assume a process's environment. Always make it explicit. The most reliable
     systems are those that create and control their own execution context, rather than implicitly inheriting
     one.
   * Future Action: For any project that shells out to a command-line tool, the first step should be to define
     and provide its required environment (CWD, environment variables via .env files, etc.) directly in the
     code that launches it.

  Lesson 2: stdin is a Loaded Gun in Subprocesses

  This was the final, definitive bug, and it is a classic trap. The "Silent Hang" was the symptom of a
  deadlock that is invisible to most debugging tools.


   * The Trap We Fell Into: We focused on what we were sending (stdout) and what was going wrong (stderr),
     but we completely ignored the third pipe: stdin. We didn't intend to write anything to the process, so
     we didn't think about it. But the claude process saw an open pipe and politely waited for it to close,
     as any well-behaved tool would.
   * The Enduring Principle: When you create a subprocess, you are responsible for all three of its standard
     streams: stdin, stdout, and stderr. If you do not explicitly manage one, it can and will cause
     unpredictable behavior.
   * Future Action: For any non-interactive subprocess that you do not intend to write to, always explicitly
     close its input stream by setting stdin=asyncio.subprocess.DEVNULL. This prevents an entire class of
     deadlocks.

  Lesson 3: When Debugging a Black Box, Isolate It


  We cannot attach a debugger to the proprietary claude executable. Therefore, we must treat it as a black
  box and use scientific methods to diagnose it.


   * The Trap We Fell Into: We started by trying to run the most complex possible command, with multiple tools
     and configurations. This created too many variables. We couldn't tell if the problem was the prompt, the
     tools, the config file, or the execution itself.
   * The Enduring Principle: The fastest way to debug a complex system is to simplify it until it works. Find
     a baseline of success, then incrementally add complexity back until it breaks. The last thing you added
     is the cause of the problem.
   * Future Action: Our breakthrough came when we finally tested a command with --no-tools. This should have
     been one of our very first steps. Always start with the "hello world" version of the command to establish
     a working baseline before testing the complex, real-world version.

  Lesson 4: Design Your API for Your Client, Not for Your Convenience

  The initial API design, which took a single "command" string, was convenient for the server (just pass it to
   shlex) but terrible for the client.


   * The Trap We Fell Into: We created an API that forced the client to be an expert in shell quoting rules.
     This is a recipe for bugs.
   * The Enduring Principle: An API is a user interface for programmers. It should be as clear, unambiguous,
     and difficult to misuse as possible.
   * Future Action: Always prefer structured data over strings that need to be parsed. Changing the API to
     {"executable": "...", "args": [...]} is a perfect example. It makes the contract explicit, removes
     ambiguity, and makes the client's job easier and safer.


  This entire exercise was a masterclass in moving from "it works on my machine" to building a truly
  robust, production-ready service. The final solution is not just functional; it is architecturally sound
  because we were forced to confront and solve each of these subtle but critical issues.