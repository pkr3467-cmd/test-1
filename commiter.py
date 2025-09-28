

import argparse
import subprocess
import time
import pathlib
import sys
import os

def run(cmd, **kwargs):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **kwargs)

def is_git_repo():
    r = run(["git", "rev-parse", "--is-inside-work-tree"])
    return r.returncode == 0 and r.stdout.strip() == "true"

def git_commit(file_path: str, message: str, env=None):
    a = run(["git", "add", file_path], env=env)
    if a.returncode != 0:
        raise RuntimeError(f"git add failed: {a.stderr.strip()}")
    c = run(["git", "commit", "-m", message], env=env)
    if c.returncode != 0:
        raise RuntimeError(f"git commit failed: {c.stderr.strip()}")
    return c.stdout.strip()

def ensure_file(path: pathlib.Path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

def normalize_line(s: str) -> str:
    # strip matching surrounding quotes if user accidentally included them
    if len(s) >= 2 and ((s[0] == s[-1]) and s[0] in ("'", '"')):
        return s[1:-1]
    return s

def read_file_text(path: pathlib.Path) -> str:
    # Use utf-8 and be resilient to bad bytes by replacing them
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        # fallback: create empty file and return empty string
        print(f"Warning: could not read {path} cleanly: {e}. Recreating/emptying file.")
        path.write_text("", encoding="utf-8")
        return ""

def write_file_text(path: pathlib.Path, txt: str):
    path.write_text(txt, encoding="utf-8", errors="replace")

def main():
    p = argparse.ArgumentParser(description="Auto toggle line and commit repeatedly (for testing).")
    p.add_argument("--file", "-f", default="toggle.txt", help="Target file to edit")
    p.add_argument("--line", "-l", default="AUTO_TOGGLE_LINE", help="Exact line to add/remove")
    p.add_argument("--iters", "-n", type=int, default=10, help="Number of toggle iterations")
    p.add_argument("--sleep", "-s", type=float, default=1.0, help="Seconds to sleep between commits")
    p.add_argument("--author-name", help="Optional: set GIT_AUTHOR_NAME for commits")
    p.add_argument("--author-email", help="Optional: set GIT_AUTHOR_EMAIL for commits")
    args = p.parse_args()

    file_path = pathlib.Path(args.file)
    ensure_file(file_path)

    if not is_git_repo():
        print("Error: current directory is not a git repo. Initialize one with `git init` and try again.", file=sys.stderr)
        sys.exit(1)

    # Normalize the line (strip accidental surrounding quotes)
    target_line = normalize_line(args.line)
    env = None
    if args.author_name or args.author_email:
        env = dict(**os.environ)
        if args.author_name:
            env["GIT_AUTHOR_NAME"] = args.author_name
            env["GIT_COMMITTER_NAME"] = args.author_name
        if args.author_email:
            env["GIT_AUTHOR_EMAIL"] = args.author_email
            env["GIT_COMMITTER_EMAIL"] = args.author_email

    print(f"Target file: {file_path}")
    print(f"Line to toggle: {target_line!r}")
    print(f"Iterations: {args.iters}, Sleep: {args.sleep}s")
    print("Commits will be labeled with 'test/auto' so they are clearly for testing.\n")

    for i in range(1, args.iters + 1):
        text = read_file_text(file_path)
        lines = text.splitlines()
        has_line = any(line == target_line for line in lines)

        try:
            if not has_line:
                # add the line at the end with newline if necessary
                if text and not text.endswith("\n"):
                    text += "\n"
                text += target_line + "\n"
                write_file_text(file_path, text)
                msg = f"cleanup"
                print(f"[{i}] Adding line -> committing: {msg}")
            else:
                # remove all exact-match lines
                new_lines = [ln for ln in lines if ln != target_line]
                out = "\n".join(new_lines)
                if new_lines:
                    out += "\n"
                write_file_text(file_path, out)
                msg = f"backup page"
                print(f"[{i}] Removing line -> committing: {msg}")

            git_commit(str(file_path), msg, env=env)
        except subprocess.CalledProcessError as e:
            print("Git command failed:", e, file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print("Error:", e, file=sys.stderr)
            sys.exit(1)

        time.sleep(args.sleep)

    print("\nDone. Inspect the history with `git log --oneline --decorate --graph`")

if __name__ == "__main__":
    main()
