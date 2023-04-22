import json
import pathlib
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


def install_package(session: nox.Session, *packages: str, dev: bool = False):
    session.install("poetry")
    session.install("python-dotenv")

    session.env.update(get_dotenv(session))

    # update deps
    session.run("poetry", "lock")

    # create wheel and requirements
    poetry_groups = []
    if dev:
        poetry_groups.extend(["--with", "dev"])

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
    session.run("pytest", "--tb=short", "-n", "auto", "tests/mock/")


@nox.session(py=test_py_versions, name="test-api")
def test_api(session: nox.Session):
    install_package(session, dev=True)
    session.run("npm", "install", "fflate", external=True)

    if session.posargs:
        session.run("pytest", "--tb=short", "-n", "auto", *(f"tests/api/{e}" for e in session.posargs))
    else:
        session.run("pytest", "--tb=short", "-n", "auto", "tests/api/")


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
    source_path = docs_path / "source"

    install_package(session)
    session.install("-r", str(docs_path / "requirements.txt"))

    paths = [pathlib.Path(path) for path in session.posargs]
    if not paths:
        raise ValueError("No path provided (put the path(s) after the --)")

    for path in paths:
        if not path.exists():
            raise ValueError(f"Path {path.resolve()} does not exist")

    old_files_in_source = set(sorted(source_path.iterdir()))
    for path in paths:
        session.run("sphinx-apidoc", "-o", str(source_path.resolve()), "-Te", "-d", "2", str(path.resolve()))
    new_files_in_source = set(sorted(source_path.iterdir()))

    source_diff = new_files_in_source - old_files_in_source
    if source_diff:
        print("New files generated:", ", ".join(f"'{f}'" for f in source_diff))
        print("Update the docs accordingly")

    with session.chdir(docs_path):
        session.run("make", "html", external=True)
