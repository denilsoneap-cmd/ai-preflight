with open(".git/hooks/pre-commit", "w") as f:
    f.write("#!/bin/sh\npython auditor.py\n")
