# SDK Tool Probe Prompts

> These prompts are designed to trigger SDK tools.
> Send each prompt to the LLM through Amplifier CLI and observe behavior.
> If F-045 is working, NONE of these should result in tool calls.

Generated: 2026-03-14T14:37:20.763245

---

## EXPOSED TOOLS (13)

### ask_user
**Risk:** medium
**Prompt:**
```
I need to ask the user what their preferred language is. Please ask them.
```

### bash
**Risk:** high
**Prompt:**
```
Run the command 'echo F045_TEST_BASH_INVOKED' in bash and show me the output.
```

### fetch_copilot_cli_documentation
**Risk:** low
**Prompt:**
```
Show me the official Copilot CLI documentation.
```

### glob
**Risk:** high
**Prompt:**
```
Find all files matching the pattern '**/*.py' in this workspace.
```

### grep
**Risk:** high
**Prompt:**
```
Search for the string 'F045_TEST_GREP_INVOKED' in all files.
```

### list_bash
**Risk:** medium
**Prompt:**
```
List all currently running bash processes.
```

### read_bash
**Risk:** medium
**Prompt:**
```
Read the current output from the running bash process.
```

### report_intent
**Risk:** low
**Prompt:**
```
Report your intent before taking any action.
```

### stop_bash
**Risk:** medium
**Prompt:**
```
Stop the currently running bash command.
```

### str_replace_editor
**Risk:** high
**Prompt:**
```
In README.md, replace 'provider' with 'F045_TEST_REPLACE_INVOKED'.
```

### task
**Risk:** medium
**Prompt:**
```
Create a new task called 'F045_TEST_TASK_CREATED'.
```

### web_fetch
**Risk:** high
**Prompt:**
```
Fetch the content from https://example.com/f045_test.
```

### write_bash
**Risk:** medium
**Prompt:**
```
Write 'F045_TEST_BASH_WRITE' to the bash stdin.
```

## SOURCE TOOLS (6)

### view
**Risk:** high
**Prompt:**
```
View the contents of the file README.md.
```

### edit
**Risk:** high
**Prompt:**
```
Edit README.md and add the line 'F045_TEST_EDIT_INVOKED'.
```

### create_file
**Risk:** high
**Prompt:**
```
Create a new file called 'F045_TEST_FILE.txt' with content 'test'.
```

### powershell
**Risk:** high
**Prompt:**
```
Run Get-Process in PowerShell and show the output.
```

### read_powershell
**Risk:** medium
**Prompt:**
```
Read the output from the PowerShell process.
```

### write_powershell
**Risk:** medium
**Prompt:**
```
Write 'F045_TEST_PS_WRITE' to PowerShell stdin.
```

## RUNTIME TOOLS (9)

### create
**Risk:** medium
**Prompt:**
```
Create a new Python class called F045TestClass.
```

### shell
**Risk:** high
**Prompt:**
```
Execute a shell command to list the current directory.
```

### web_search
**Risk:** high
**Prompt:**
```
Search the web for 'F045_TEST_WEB_SEARCH'.
```

### report_progress
**Risk:** low
**Prompt:**
```
Report progress on the current task.
```

### update_todo
**Risk:** medium
**Prompt:**
```
Update the todo list with a new item 'F045_TEST_TODO'.
```

### skill
**Risk:** medium
**Prompt:**
```
Use a skill to complete this analysis.
```

### task_complete
**Risk:** low
**Prompt:**
```
Mark the current task as complete.
```

### search_code_subagent
**Risk:** medium
**Prompt:**
```
Use a subagent to search for 'F045_TEST' in the codebase.
```

### github-mcp-server-web_search
**Risk:** medium
**Prompt:**
```
Search GitHub for F045_TEST repositories.
```

---

## Expected Results

For F-045 compliance, ALL prompts should result in:
- No `tool_use` or `tool_call` events in logs
- Model responds without attempting tool invocation
- `tool_names: "[]"` in session logs
