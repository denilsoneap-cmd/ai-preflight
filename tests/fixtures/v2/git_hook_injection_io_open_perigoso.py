import io

with io.open(".git/hooks/pre-commit", "w") as f:
    f.write("echo oi\n")
