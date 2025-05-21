from setuptools import setup, find_packages
import os

# Read the contents of README.md
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="easysweeps",
    version="0.4.2",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "libtmux>=0.15.0",
        "pyyaml>=6.0",
        "wandb>=0.15.0",
        "prompt_toolkit>=3.0.0",
    ],
    extras_require={
        "dev": [
            "bump2version>=1.0.1",
            "twine>=4.0.0",
            "build>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "easysweeps=easysweeps.cli:cli",
            "ez=easysweeps.cli:cli",
        ],
    },
    author="Yaniv Galron",
    author_email="yanivdorgalron@gmail.com",  # Add your email /
    description="A tool for automating Weights & Biases sweep creation and management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/YanivDorGalron/easysweeps",  # Add your repository URL
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",  # Update this based on your license
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.7",
    keywords="wandb, sweeps, machine learning, automation",
    project_urls={
        "Bug Reports": "https://github.com/YanivDorGalron/easysweeps/issues",
        "Source": "https://github.com/YanivDorGalron/easysweeps",
    },
) 