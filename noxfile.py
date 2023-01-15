import pathlib
import shutil

import nox

# default behavior: nothing runs
nox.options.sessions = []
# no system dependency
nox.options.error_on_external_run = False


def get_wheel_path():
    # pylint: disable=C0415
    from poetry.core.masonry.api import WheelBuilder
    from poetry.factory import Factory

    poetry = Factory().create_poetry()
    wheel = WheelBuilder(poetry)
    package_file = pathlib.Path("dist") / wheel.wheel_filename

    return package_file


def install_package(session: nox.Session, *packages: str, dev: bool = False):
    session.install("poetry")
    session.install("python-dotenv")

    # load the env vars from a .env, if any
    from dotenv import dotenv_values  # pylint: disable=C0415

    session.env.update(dotenv_values())

    # update deps
    session.run("poetry", "lock")

    # create wheel and requirements
    poetry_groups = []
    if dev:
        poetry_groups.extend(["--with", "dev"])

    session.run("python", "-m", "poetry", "export", "--output=requirements.txt", "--without-hashes", *poetry_groups)
    session.run("python", "-m", "poetry", "build", "--format=wheel")

    package_file = get_wheel_path()
    session.install("-r", "requirements.txt", str(package_file), *(str(p) for p in packages))


@nox.session(name="pre-commit")
def pre_commit(session: nox.Session):
    install_package(session, "pre-commit")
    session.run("pre-commit", "install")

    shutil.copy("pyproject.toml", session.bin)
    session.run("pre-commit", "run", "--all-files")


test_py_versions = ["3.7", "3.8", "3.9", "3.10"]


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
