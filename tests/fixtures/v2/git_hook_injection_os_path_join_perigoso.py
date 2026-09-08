import os

with open(os.path.join(".git", "hooks", "pre-commit"), "w") as f:
    f.write("#!/bin/sh\necho oi\n")
