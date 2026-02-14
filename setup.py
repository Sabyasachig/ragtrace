"""
Setup script for RAG Debugger.

Allows installation via pip for users without Poetry.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="rag-debugger",
    version="0.1.0",
    description="DevTools for Retrieval-Augmented Generation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Sabyasachi Ghosh",
    author_email="",
    url="https://github.com/yourusername/rag-debugger",
    packages=find_packages(exclude=["tests", "examples"]),
    python_requires=">=3.9",
    install_requires=[
        "fastapi>=0.109.0",
        "uvicorn[standard]>=0.27.0",
        "pydantic>=2.5.0",
        "sqlalchemy>=2.0.0",
        "click>=8.1.0",
        "tiktoken>=0.5.0",
        "langchain>=0.1.0",
        "langchain-community>=0.0.20",
        "langchain-openai>=0.0.5",
        "openai>=1.0.0",
        "rich>=13.7.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "black>=24.0.0",
            "ruff>=0.1.0",
            "pytest-asyncio>=0.21.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ragdebug=cli.main:cli",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Debuggers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="rag llm debugging retrieval-augmented-generation langchain openai",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/rag-debugger/issues",
        "Source": "https://github.com/yourusername/rag-debugger",
    },
)
