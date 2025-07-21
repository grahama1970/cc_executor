# Gemini Stress Test Prompt

You are a skilled AI project architect.

Your task is to simulate an entire year-long global product launch plan.

In this simulation, there are:

- 6 regional offices:
  - North America
  - Europe
  - Asia
  - South America
  - Africa
  - Australia

- 20 cross-functional stakeholders:
  - Executives
  - Engineers
  - Designers
  - Sales
  - Support

- 50 unique product features launching across multiple timelines

---

## Instructions

1. Break down the plan into 4 quarters (Q1 to Q4).
2. For each quarter, define **3–5 major milestones**.
3. For each milestone, define the following:
   - A short description
   - Start and end dates
   - Assigned leads
   - Dependencies and region(s) affected
   - Estimated effort in person-weeks

4. After establishing the quarterly plans:
   - Generate a matrix of responsibility showing which stakeholders are involved in which milestones.
   - Include a **JSON summary** for each regional office showing:
     - Total milestones owned
     - Total effort (in person-weeks)
     - Features covered

5. Return **only the output as a complete JSON object**.

If output is too large, begin with Q1 and stream the remaining quarters.

---

## 🎯 JSON Schema

```
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
  "responsibility_matrix": {
    "Alice": ["Q1: Launch Alpha", "Q2: Beta Sprint"]
  },
  "regional_summaries": {
    "North America": {
      "milestones": 8,
      "total_effort": 460,
      "features_covered": ["Feature A", "Feature D", "..."]
    }
  }
}
```

---

## Output Requirements

- ⏱ Begin generating response immediately.
- 📦 If output exceeds context limit, return Q1 first and stream/continue.
- ❌ **DO NOT include explanation or commentary. Return JSON only.**
```

