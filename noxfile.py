import json
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
