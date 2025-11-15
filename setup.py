"""Setup script for AI Cross-Poster"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ai-cross-poster",
    version="1.0.0",
    author="Your Name",
    description="Analyzes images to create optimized listings on multiple resell platforms",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ai-cross-poster",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
    ],
    extras_require={
        "mercari-automation": ["playwright>=1.40.0"],
        "image-processing": ["Pillow>=10.0.0"],
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "python-dotenv>=1.0.0",
        ],
    },
)
