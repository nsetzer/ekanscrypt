
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

packages = setuptools.find_packages()
print(packages)
entry_points={
    'console_scripts': [
        'ekans=ekanscrypt.__main__:main',
    ],
}
print(entry_points)

setuptools.setup(
    name="ekanscrypt", # Replace with your own username
    version="0.1.0",
    author="Nick Setzer",
    author_email="nicksetzer@github.com",
    description="python compatible scripting language",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nsetzer/ekanscrypt",
    packages=packages,
    entry_points=entry_points,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.4',
)