from setuptools import setup, find_packages

setup(
    name="film_scanner",
    version="0.1.0",
    description="A tool for scanning film negatives using an Olympus camera",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "olympuswifi>=0.1.0",
        "Pillow>=9.0.0",
        "numpy>=1.20.0",
    ],
    entry_points={
        "console_scripts": [
            "film-scanner=main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)
