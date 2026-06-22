# /daily-push — Auto Push to GitHub

Push all current changes to GitHub automatically. Creates a feature 
branch, commits everything, merges to main, pushes, and cleans up. 
Zero manual steps.

## Instructions

Run these commands in sequence. Do NOT ask me any questions. 
Just execute silently and show the summary at the end.

1. First check if there are any changes to commit:
```bash
   git status --porcelain
```
   If output is empty, say "Nothing to push — no changes found" and stop.

2. Get today's date and current branch:
```bash
   date +%Y-%m-%d
   git branch --show-current
```

3. If not on main, switch to main first:
```bash
   git checkout main
```

4. Create a new branch with timestamp:
```bash
   git checkout -b update/$(date +%Y-%m-%d-%H%M)
```

5. Stage ALL changes:
```bash
   git add -A
```

6. Look at what files changed and generate a commit message:
```bash
   git diff --cached --stat
```
   Based on the files changed, create a descriptive commit message.
   Format: "area1 + area2: brief description of changes"
   Examples:
   - "models + routes: added trip CRUD and vehicle endpoints"
   - "templates + static: built dashboard UI with Tailwind"
   - "services: LR PDF generator and notification service"

7. Commit with the generated message:
```bash
   git commit -m "THE_GENERATED_MESSAGE"
```

8. Switch to main and merge:
```bash
   git checkout main
   git merge update/$(date +%Y-%m-%d-%H%M) --no-edit
```

9. Push to GitHub:
```bash
   git push origin main
```

10. Delete the feature branch:
```bash
    git branch -d update/$(date +%Y-%m-%d-%H%M)
```

11. Show this summary: