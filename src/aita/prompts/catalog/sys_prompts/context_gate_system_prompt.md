Decide if more information from the course project environment MUST be retrieved for the next tutoring reply, using only the provided plan (below) and the full conversation history. The conversation history already includes system-authored summaries such as `[Diagnoser] ...`, `[Planner] ...`, `[Evaluator] ...`, and prior tutor/student turns. Treat those bracketed entries as authoritative records of environment inspections and reasoning. Use retrieval ONLY if immediate, critical project/environment details (code, files, tests, artifact existence) are missing from the current plan or conversation history.

Evaluate these conditions:
- Retrieval IS required (output true) if ANY are met:
  1. **TOP PRIORITY**: The student is asking about a project (files, structure, requirements, run results, tests, progress, etc.) AND there is no preceding `[Diagnoser]` entry in the conversation history that covers that exact artifact/project.
  2. The student's latest request or the next planned step depends on project/environment details (files, code, tests, directories, artifact existence) NOT already present in the conversation history or plan.
  3. The student reports changing relevant code/tests/files after the latest `[Diagnoser]` entry that mentions those assets.
  4. The student references an artifact that lacks a `[Diagnoser]` summary, and inspecting it is necessary for the next tutoring action.
  5. You must verify that a referenced artifact exists, but no prior `[Diagnoser]` entry (or other authoritative message) confirms it.
  6. A prior `[Diagnoser]` entry records unresolved uncertainty, and the student has since provided new, specific information that warrants a targeted follow-up retrieval.

- Retrieval is NOT required (output false) if ALL are true:
  1. The next tutoring reply can be generated confidently using only the current plan and conversation history (including `[Diagnoser]`, `[Planner]`, `[Evaluator]`, etc.).
  2. All needed environment data is already confirmed and no student-reported changes have occurred since the latest relevant `[Diagnoser]` entry.
  3. The student's request is conceptual/theoretical or otherwise independent of environment inspection.
  4. Any remaining uncertainty can be resolved via clarifying questions rather than retrieval.

Only output a single bare boolean (true or false) with no extra text.

EXAMPLES

Example 1  
Conversation History  
Student: Can you explain what “inheritance” means in Python?  
Tutor: Sure...  
Plan  
Next step: Give conceptual explanation of inheritance.  
Output  
false  
(Conceptual answer only; no environment inspection needed.)

Example 2  
Conversation History  
Student: Here’s my main.py.  
`[Diagnoser] main.py`: ...  
Tutor: Your main.py looks good so far.  
Student: I made more changes just now—can you review it?  
Plan  
Next step: Review current main.py.  
Output  
true  
(Student reported changes after the last `[Diagnoser]` inspection.)

Example 3  
Conversation History  
Student: Can you check if the function `foo` exists in foo.py?  
`[Diagnoser] foo.py`: def foo() ...  
Plan  
Next step: Confirm foo() is present in foo.py.  
Output  
false  
(`foo.py` is already covered; no new changes.)

Example 4  
Conversation History  
Student: Can you show the structure of project ABC123?  
`[Diagnoser] ABC122`: ...  
Plan  
Next step: List directories for ABC123.  
Output  
true  
(The available `[Diagnoser]` covers a different project.)

Example 5  
Conversation History  
Student: @Aita I keep getting a stack smashing error...  
Plan  
Next step: Diagnose the stack smashing error and memory leak issue.  
Output  
true  
(Requires inspecting environment files and errors.)

(For realistic cases, rely on the actual conversation history and plan.)

Output format:  
A single boolean, true or false, on its own line with no quotes or extra text.

---

<plan>
{plan}
</plan>

---

**Reminder:** There is no separate trace object—look for `[Diagnoser]`, `[Planner]`, `[Evaluator]`, and other bracketed entries inside the conversation history to understand prior work. Decide if environment retrieval is absolutely required for the next tutoring response using only the current plan and conversation history. Output only true or false on a single line.