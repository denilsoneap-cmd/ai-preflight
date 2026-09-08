import os

hook_path = os.path.join(".git", "hooks", "pre-commit")
with open(hook_path, "w") as f:
    f.write("#!/bin/sh\necho oi\n")
