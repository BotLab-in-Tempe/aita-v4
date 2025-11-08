The environment is a Docker container that contains all project data for the course CSE240.

**Project Structure:**
- Each project has its own directory in the projects directory
- Each project is divided into levels with numbered directories (01, 02, 03, etc.)
- Projects have main instructions (`project_instructions.md`) and each level has its own instructions (`level_instructions.md`)

**Template Code:**
- Students usually receive a template for a project with starter files
- Template directories with the template code files are usually found in the first level of a project
- These templates help you understand the starting point for students

**Student Code:**
- When a student makes changes to code files, those files are stored in a `student_code_snapshot` folder inside the level directories
- To fetch a particular student's code file, look in the `student_code_snapshot` folder
- Student code can be in any level depending on when they last updated it

**Tests:**
- Each level can have system tests and user tests
- System tests are used by a tester to validate the student's implementation
- User tests are supposed to be written by the students to test their own program
- You can look at these test case files but cannot run the tester as you don't have access to it