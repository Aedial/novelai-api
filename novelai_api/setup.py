import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name = "quicksample",
    version = "0.2",
    author="Arthus Leroy",
    description= " Quicksample Test Package for SQLShack Demo",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    packages = setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires = '>=3.7',
    py_modules = ["quicksample"],
    package_dir = {'':'quicksample/src'},
    install_requires = [
		""
	]
)