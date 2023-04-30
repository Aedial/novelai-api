import json
import pathlib
import re
import shutil

import nox

# default behavior: nothing runs
nox.options.sessions = []
# no system dependency
nox.options.error_on_external_run = False


def get_wheel_path(session: nox.Session):
    path_str = session.run("python", "noxfile_utils.py", "wheel_path", silent=True)
    if not path_str:
        raise RuntimeError("get_wheel_path util failed")

    return path_str


def get_dotenv(session: nox.Session):
    dotenv_str = session.run("python", "noxfile_utils.py", "dotenv", silent=True)
    if not dotenv_str:
        raise RuntimeError("get_dotenv util failed")

    return json.loads(dotenv_str)


def install_package(session: nox.Session, *packages: str, dev: bool = False, docs: bool = False):
    session.install("poetry")
    session.install("python-dotenv")

    session.env.update(get_dotenv(session))

    # update deps
    session.run("poetry", "lock")

    # create wheel and requirements
    poetry_groups = []
    if dev:
        poetry_groups.extend(["--with", "dev"])
    if docs:
        poetry_groups.extend(["--with", "docs"])

    session.run("python", "-m", "poetry", "export", "--output=requirements.txt", "--without-hashes", *poetry_groups)
    session.run("python", "-m", "poetry", "build", "--format=wheel")

    package_file = get_wheel_path(session)
    session.install("-r", "requirements.txt", package_file, *(str(p) for p in packages))

    username = session.env.get("NAI_USERNAME", "<UNKNOWN>")
    version = session.run("python", "--version", silent=True)
    print(f"Using {username} with {version}")


@nox.session(name="pre-commit")
def pre_commit(session: nox.Session):
    install_package(session, "pre-commit")
    session.run("pre-commit", "install")

    shutil.copy("pyproject.toml", session.bin)
    session.run("pre-commit", "run", "--all-files")


test_py_versions = ["3.7", "3.8", "3.9", "3.10", "3.11"]


@nox.session(py=test_py_versions, name="test-mock")
def test_mock(session: nox.Session):
    install_package(session, dev=True)
    session.run("pytest", "tests/mock/")


@nox.session(py=test_py_versions, name="test-api")
def test_api(session: nox.Session):
    install_package(session, dev=True)
    session.run("npm", "install", "fflate", external=True)

    if session.posargs:
        session.run("pytest", *(f"tests/api/{e}" for e in session.posargs))
    else:
        session.run("pytest", "tests/api/")


@nox.session()
def run(session: nox.Session):
    files = session.posargs

    for file in files:
        if ".." in file:
            raise ValueError(f"Cannot run script {file}: outside of the repo")

    install_package(session)

    for file in files:
        session.run("python", file)


@nox.session(name="build-docs")
def build_docs(session: nox.Session):
    docs_path = pathlib.Path(__file__).parent / "docs"

    install_package(session, dev=True, docs=True)

    with session.chdir(docs_path):
        session.run("make", "html", external=True)


@nox.session(name="bump-version")
def bump_version(session: nox.Session):
    if len(session.posargs) < 1:
        raise ValueError("Expected `nox -s bump-version -- major|minor|patch`")

    bump = session.posargs[0]

    if bump not in ("major", "minor", "patch"):
        raise ValueError(f"Expected bump rule to be 'major', 'minor', or 'patch', got '{bump}'")

    # Check for staged files (you don't want to accidentally commit them)
    staged_files = session.run("git", "diff", "--name-only", "--cached", external=True, silent=True)
    if staged_files:
        raise RuntimeError(f"Staged files, commit them before bumping version:\n{staged_files}")

    # Bump the pyproject.toml and get the versions
    session.install("poetry")
    current_version = session.run("poetry", "version", "-s", silent=True).strip()
    session.run("poetry", "version", bump)
    bumped_version = session.run("poetry", "version", "-s", silent=True).strip()

    # Modify the version in README's badges
    rgx_badge = re.compile(r"(https://img.shields.io[^)]+?)(v\d+(?:\.\d+(?:\.\d+)?)?)")
    with open("README.md", "r+", encoding="utf-8") as f:
        readme = f.read()
        readme = rgx_badge.sub(f"\\1v{bumped_version}", readme)

        f.truncate(0)
        f.seek(0)
        f.write(readme)

    # Commit the bump
    commit_message = f"[MISC] Bump version - {bump}: {current_version} -> {bumped_version}"
    session.run("git", "add", "README.md", "pyproject.toml", external=True)
    session.run("git", "commit", "-m", commit_message, external=True)

    # Commit the tag
    session.run("git", "tag", "-a", f"v{bumped_version}", external=True)

    session.log(
        f"You can now push the commit and the tag with `git push origin v{bumped_version}`.\n"
        "Ensure you're really ready to push with `git status` and `git log`."
    )
