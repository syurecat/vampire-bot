import subprocess

def get_git_version():
    try:
        tag = subprocess.check_output(['git', 'describe', '--tags', '--always'], stderr=subprocess.DEVNULL).decode().strip()
        return tag
    except Exception:
        return 'unknown'

VERSION = get_git_version()
