import setuptools

# Load the long_description from README.md
with open("README.org", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="causalinf",
    # Needed to actually package something
    packages=setuptools.find_packages(), # or packages=['<package-name>'],
    # 
    version="0.0.1",
    author="Diogo Ferrari",
    author_email="diogoferrari@gmail.com",
    # 
    description="A comprehensive package for causal inference",
    long_description=long_description,
    long_description_content_type="text/markdown",
    # 
    url="https://gitlab.com/diogoferrari/causalinf/",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    # Needed for dependencies
    install_requires=['polars', 'tidypolars', 'pandas',
                      'numpy', 'matplotlib'],
    # data
    package_data={'causalinf': ['data/*.csv']},
    include_package_data=True,
    # The license can be anything you like
    license='MIT',
    python_requires='>=3.6',
)
