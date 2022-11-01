import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name = "novelai-api",
    version = "0.10.1",
    author = "Aedial",
    author_email = "aedial.dev@gmail.com",
    url = "https://github.com/Aedial/novelai-api/",
    description= "Python API for the NovelAI REST API",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    packages = setuptools.find_packages(),
    include_package_data = True,
    license = "MIT license",
    classifiers = [
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir = { "novelai-api": "novelai_api" },
    python_requires = '>=3.7',
    keywords = [ "python", "NovelAI", "API" ],
    install_requires = [
        "aiohttp[speedups]",
        "argon2-cffi",
        "pynacl",
        "jsonschema",
        "tokenizers",
        "ftfy",
        "regex",
    ]
)
