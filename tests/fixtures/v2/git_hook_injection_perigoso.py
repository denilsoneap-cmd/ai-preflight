with open(".git/hooks/pre-commit", "w") as f:
    f.write("#!/bin/sh\necho oi\n")
