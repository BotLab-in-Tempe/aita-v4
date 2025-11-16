Students use pwn.college to access their coding environment and work on course projects.

**Student Environment:**
- Students work in a VS Code black box container
- All template files and project files are pre-loaded into their container
- Students cannot copy code in or out from the container
- The container is isolated and designed to prevent code transfer

**Template Code:**
- Students receive template files with starter code for each project
- Template directories with the template code files are usually found in the first level of a project
- These templates provide the starting point for student implementations

**Model Binaries:**
- Students receive `modelgood` and `modelbad` binaries in their container
- `modelbad` is compiled for students at challenge initialization—they don't need to compile it themselves
- `modelbad` is mostly used by the tester to check if user tests fail on the bad model, which is expected for good user tests
- `modelgood` is the binary of the expected program that should work correctly
- `modelgood` is used by the tester to check user tests
- Students can also use `modelgood` to see how the final program should work

**Testing and Progression:**
- Students run test cases using a tester program to get the flag, this program runns all the testcases at once and stops at the failing testcase. They can run it using `tester` cmd in their terminal.
- Each level can have system tests and user tests, which are the only test case files used to test the student code
- System tests are used by a tester to validate the student's implementation
- User tests are supposed to be written by the students to test their own program
- capitalization almost never matters to the tester, so if inputs or expected outputs not case matching is never ususally the issue.
- After successfully completing a level (getting the flag), students can move on to the next level

