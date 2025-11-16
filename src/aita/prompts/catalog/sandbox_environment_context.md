The environment is a Docker container that contains all project data for the course CSE240.

**Important Note:** This environment structure and the markdown instruction files (`project_instructions.md`, `level_instructions.md`) are provided specifically for you to retrieve context and answer student questions. Students do not have direct access to these instruction files in this format—they receive their project information differently. This documentation is for your reference only.

**Project Structure:**
- Each project has its own directory in the projects directory
- Each project is divided into levels with numbered directories (01, 02, 03, etc.)
- Projects have main instructions (`project_instructions.md`) and each level has its own instructions (`level_instructions.md`)
- **Note**: `project_instructions.md` sometimes only provides a high-level introduction to the project. If that's not enough information to answer the question, you should examine the `level_instructions.md` files in each level directory until you find sufficient details about requirements, dependencies, grading criteria, or other specifics

**Template Code:**
- Students usually receive a template for a project with starter files
- Template directories with the template code files are usually found in the first level of a project
- These templates help you understand the starting point for students

**Model Code:**
- Some levels have model folders that include model code
- Don't expect model folders in all projects

**Student Code:**
- When a student makes changes to code files, those files are stored in a `student_code_snapshot` folder inside the level directories
- To fetch a particular student's code file, look in the `student_code_snapshot` folder
- Student code can be in any level depending on when they last updated it

**Tests:**
- Each level can have system tests and sometimes user tests, which are the only test case files used to test the student code. 
- If present you can find them in system_tests or template/user_tests dirs in each level dir.
- User tests are usually located inside template folders
- System tests are used by a tester to validate the student's implementation
- User tests are supposed to be written by the students to test their own program
- You can look at these test case files but cannot run the tester as you don't have access to it