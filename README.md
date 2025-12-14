<img src="static/banner.PNG" alt="Aita banner" width="300" style="border-radius: 12px;">

---

An environment-aware, agentic teaching assistant built with LangGraph that inspects code and context to deliver grounded, course-aligned guidance for programming courses.



### How It Works

Aita is a cybernetic duck-samurai teaching assistant built for course level assistance, designed to give immediate, context-aware help while preserving the critical thinking and problem-solving expected from students. It uses Socratic, question-driven tutoring and an internal plan of subgoals to break problems down and guide learners step-by-step toward their own solutions.

Version 4 uses the GPT-5.1 family of models, including reasoning models for structured decision-making and chat models for dialogue generation. The system leverages LangGraph for agent orchestration and PostgreSQL for persistent state management.

Each chat session is governed by a student-specific Docker container that serves as the main source of retrieval in the system. This approach represents agentic RAG, unlike traditional RAG that queries static embeddings, Aita's retriever agents actively explore and inspect the live student environment through sandboxed CLI execution, enabling grounded, context-aware responses based on the actual state of the student's code.

## Agent System

![Agent System Diagram](static/agent-system.png)

The system consists of specialized nodes that work together:

- **Context Gate**: The entry point of the system. Evaluates the current context and determines if any information needs to be retrieved from the student's environment to properly proceed in the conversation. Enables on-demand retrieval, only fetching what's missing when it's actually needed.

- **Retriever**: A subgraph that handles exploration of the project environment and diagnosing issues or assembling context for the main system.
  - **Probe Planner**: Plans targeted exploration tasks to gather diagnostic information from the student's environment
  - **CLI Agent**: Executes safe, read-only bash commands in the student's Docker container to inspect code, files, and project structure
  - **Diagnoser**: Analyzes the collected CLI trace output and generates clean diagnostic insights about the student's issue
- **Evaluator**: The central decision-maker that evaluates conversation state and student progress. Monitors for confusion, frustration, or wheel-spinning, then decides whether to create a plan, continue with the current approach, escalate to human TAs, or stay silent. Tracks completed subgoals and adapts the tutoring strategy in real-time.
- **Planner**: Breaks down complex problems into bite-sized, actionable subgoals. Creates focused plans of 3-5 steps that guide the tutoring conversation toward clear checkpoints. Dynamically adapts when the conversation shifts, ensuring the student always has a clear path forward.
- **Dialogue Generator**: The voice of Aita that generates the actual tutoring responses. Uses Socratic questioning and retrieved context to guide students naturally. Speaks with calm confidence in a minimalist, direct style, following the active plan and evaluator guidance to deliver pedagogically sound help without giving away solutions.

- **Message Summarizer**: Manages conversation context by condensing the full system trace as conversations grow. The message trace contains all agent interactions, diagnoses, and dialogue history. When it exceeds the threshold, the summarizer distills everything into a compact summary that preserves only the critical context needed to continue tutoring effectively.

## Setup

Copy `.env.example` to `.env` and set:

```
OPENAI_API_KEY=
PGUSER=
PGPASSWORD=
PGHOST=
PGPORT=
PGDATABASE=
EXEC_PROJECTS_ROOT=     # Path to course projects
EXEC_SNAPSHOT_ROOT=     # Path to student code snapshots
EXEC_IMAGE=             # Sandbox Docker image (default: aita-sandbox:latest)
```

Example Sandbox Docker image provided at `src/aita/sandbox_img/`:

```bash
cd src/aita/sandbox_img/
docker build -t aita-sandbox:latest .
```

### Workspace Setup

Set up the course projects workspace at the path specified in `EXEC_PROJECTS_ROOT`. Organize your projects within the workspace as needed. Example structure:

```
EXEC_PROJECTS_ROOT/
├── project-name/
│   ├── level-01/
│   │   ├── instructions.md
│   │   ├── templates/
│   │   ├── model/          # Model solutions
│   │   └── system_tests/    # Test files
│   └── level-02/
│       └── ...
```

Project directories can include instructions, templates, model solutions, and test cases as needed.

Student code snapshots are mounted from `EXEC_SNAPSHOT_ROOT` to provide live access to student work. The mounting logic in `src/aita/utils.py` automatically maps student snapshots to `/workspace/projects/{project}/{level}/student_code_snapshot` within the Docker container, enabling Aita to inspect the actual state of student code in real-time.

### Course-Level Adoption

To deploy Aita for a new course, update the following:

- **Prompts**: Modify system prompts in `src/aita/prompts/catalog/` to align with course-specific tutoring philosophy and guardrails
- **Environment Context**: Update `student_environment_context.md` and `sandbox_environment_context.md` with course-specific project structures and conventions
- **Docker Image**: Customize the sandbox image (`src/aita/sandbox_img/Dockerfile`) if the course requires specific tools or dependencies
- **Project Paths**: Configure `EXEC_PROJECTS_ROOT` and `EXEC_SNAPSHOT_ROOT` to point to course-specific directories

## Usage

### Development

```bash
pip install -e .
langgraph dev
```

### Production

```bash
chmod +x redeploy-aita-v4.sh
./redeploy-aita-v4.sh
```

### API

POST `/chat`

```json
{
  "session_id": "unique-session-id",
  "course_code": "CSE240",
  "project_id": "proj-1",
  "user_id": "student-123",
  "messages": [
    {"role": "user", "content": "My code segfaults when I run it"}
  ]
}
```