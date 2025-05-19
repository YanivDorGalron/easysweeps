from setuptools import setup, find_packages

setup(
    name="easysweeps",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "libtmux>=0.15.0",
        "pyyaml>=6.0",
        "wandb>=0.15.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "easysweeps=easysweeps.cli:cli",
            "es=easysweeps.cli:cli",
        ],
    },
    author="Yaniv Galron",
    description="A tool for automating Weights & Biases sweep creation and management",
    python_requires=">=3.7",
) 