from setuptools import setup, find_packages

setup(name='SAUCE',
      version='1.0',
      description='SECAR Analysis',
      author='Caleb Marshall',
      email='marshalc@frib.msu.edu',
      packages=find_packages(),
      install_requires = [
          'numpy', 'numba', 'pandas', 'matplotlib',
          'emcee', 'tables'
          ]
)
