from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ztalk",
    version="1.0.0",
    author="ZTalk Developers",
    author_email="user@example.com",
    description="Cross-platform peer-to-peer chat application",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ztalk",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Communications :: Chat",
        "Topic :: Internet",
    ],
    python_requires=">=3.6",
    install_requires=[
        "zeroconf",
        "netifaces",
        "customtkinter>=5.2.0",
        "pillow",
    ],
    entry_points={
        "console_scripts": [
            "ztalk=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.png", "*.jpg", "*.ico", "*.json"],
    },
) 