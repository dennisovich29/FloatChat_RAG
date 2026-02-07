"""
FloatChat RAG - Argo Float Data Pipeline with RAG Capabilities
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="floatchat-rag",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Argo Float Data Pipeline with RAG capabilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/FloatChat_RAG",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Oceanography",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "xarray>=2023.1.0",
        "netCDF4>=1.6.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "sqlalchemy>=2.0.0",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "pyarrow>=12.0.0",
        "chromadb>=0.4.0",
        "sentence-transformers>=2.2.0",
        "faiss-cpu>=1.7.4",
        "tqdm>=4.65.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "floatchat-pipeline=scripts.run_pipeline:main",
            "floatchat-index=scripts.index_vectors:main",
        ],
    },
)
