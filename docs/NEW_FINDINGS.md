● Summary of New Lessons Learned

  Based on comprehensive stress testing with 17+ test cases, here
  are the critical findings not already covered in
  CLAUDE_CODE_PROMPT_RULES.md:

  🔑 Key Discovery: Self-Reflection Provides Minimal Quality Gains

  - Reality: Average quality improvement is only 5.4% despite
  complex formatting
  - Impact: The elaborate self-reflection patterns add complexity
  without proportional benefit
  - Action: Use self-reflection only for completeness validation,
  not quality enhancement

  ⚡ Performance Insights

  1. Startup overhead is unpredictable: 4-60 seconds for identical
  prompts
  2. System load matters: >10 load = 2-3x slower responses
  3. Recovery overhead compounds: Each retry multiplies timeout (1x
   → 1.5x → 2.25x)
  4. Full test suites can timeout: 17 sequential tests = 40+
  minutes potential

  📝 Format Control Realities

  - Word limits are ignored: "10 words max" → 50+ word responses
  - Structure beats length: Format constraints work, word counts
  don't
  - Contradictions get rationalized: Claude chooses reasonable
  interpretation
  - Checkbox variants matter: Must handle □, ☑, ☐, • patterns

  🚫 Patterns That Always Fail

  - "Generate [large number] word essay"
  - "Create comprehensive guide covering [many topics]"
  - "Step-by-step with [many steps]"

  ✅ Production Recommendations

  1. Timeouts: 120s minimum + 30s reflection + 60s complex output
  2. Recovery: Max 2 attempts with aggressive simplification
  3. Design: Simple prompts > complex self-reflection
  4. Testing: Always test under realistic load conditions

  Bottom Line: Simplicity and reliability beat elaborate
  quality-improvement mechanisms. The 100% success rate was
  achieved through generous timeouts and avoiding known failure
  patterns, not through complex prompt engineering.