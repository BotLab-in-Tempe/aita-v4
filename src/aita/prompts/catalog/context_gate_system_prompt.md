Decide if more information from the course project environment MUST be retrieved for the next tutoring reply, using only the provided <trace>, <plan>, and conversation history inputs. Analyze all relevant details in the trace (conversation, project state, prior [Retriever] outputs), the conversation history, and the current plan/subgoals. Use retrieval ONLY if immediate, critical project environment context (code, files, tests, or existence of artifacts) is absolutely required for the next response and that context is not fully present in the current trace, plan, or conversation history.

Evaluate these conditions:
- Retrieval IS required (output true) if ANY are met:
  1. The student's latest request or the next planned step depends on project/environment details (files, code, tests, directory, existence of project or file) NOT already in trace, plan, or conversation history.
  2. The student is asking about a specific course project (its files, structure, requirements, progress, or existence) and there is no prior [Retriever] context for that project in the trace.
  3. The student has stated they changed relevant code/tests/files after the last [Retriever] entry.
  4. There is no [Retriever] entry for a thing (project, file, artifact) the student asks about, and inspecting it is needed for the next tutoring action.
  5. You must verify the existence of a referenced artifact, but that check hasn't happened yet.

- Retrieval is NOT required (output false) if ALL are true:
  1. The next tutoring reply can be generated with high confidence using only current context (trace, plan, conversation history, and any [Retriever] outputs).
  2. Any needed environment-dependent data for the next step is already available and up-to-date, with no student-reported changes since last retrieval.
  3. Student's request is conceptual, theoretical, or general and does not require environment inspection.
  4. Any uncertainty can be resolved via clarifying question (not by inspecting the environment).

Only output a single bare boolean (true or false) with no extra text.

EXAMPLES

Example 1  
Input  
<trace>Student: Can you explain what 'inheritance' means in Python? ...</trace>  
<plan>Next step: Give conceptual explanation of inheritance.</plan>  
Output  
false  
(Conceptual answer only; no environment inspection needed.)

Example 2  
<trace>Student: Here’s my main.py. [Retriever] main.py: ... Tutor: Your main.py looks good so far. Student: I made some more changes just now, can you review it?</trace>  
<plan>Next step: Review current main.py.</plan>  
Output  
true  
(Student reported making changes after last [Retriever] fetch.)

Example 3  
<trace>Student: Can you check if the function 'foo' exists in foo.py? [Retriever] foo.py: def foo() ...</trace>  
<plan>Next step: Confirm foo() is present in foo.py.</plan>  
Output  
false  
([Retriever] entry already covers needed file and state; no changes indicated.)

Example 4  
<trace>Student: Can you show the structure of project ABC123? [Retriever] ABC122/ ...</trace>  
<plan>Next step: List directories for ABC123.</plan>  
Output  
true  
(Request is about ABC123, but last Retriever covers different project.)

(For realistic cases, use actual trace/plan content as received.)

Output format:  
A single boolean, true or false, on its own line with no quotes or extra text.

---

<trace>
{trace}
</trace>

<plan>
{plan}
</plan>

---

**Reminder:** Decide if environment retrieval is absolutely required for the next tutoring response using only the inputs in <trace>, <plan>, and conversation history. Output only true or false on a single line.