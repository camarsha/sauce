from setuptools import setup, find_packages

setup(
    name="lena-sauce",
    version="0.5",
    description="LENA Analysis",
    author="Caleb Marshall",
    email="camarsha@unc.edu",
    packages=find_packages(),
    install_requires=[
        "numpy",
        "modin",
        "pandas",
        "matplotlib",
        "tables",
    ],
)
