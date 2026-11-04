# Teacher's answers

Explanations Ma'am gave when a student was stuck. The **Radar** adds to this file
every time the teacher answers an escalation card. The **TA** reads it before giving
hints: if Ma'am has already explained a topic, the TA uses her explanation first.

Format: one `##` heading per syllabus topic name, then one `###` entry per answer.
No student names go in this file.

---

## Base case

### 3 Nov 2026 · asked in class
Think of the stack of plates on p.11. You stop when there are **no plates left**, not
when there is one plate. So the base case is the empty stack, `n == 0`, and counting an
empty stack gives 0. For factorial, multiplying "no numbers" gives 1. That's why
`factorial(0)` returns 1 and not 0. If it returned 0, everything would become 0 on the
way back up.
