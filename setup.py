# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    requirements = [
        line for line in f.readlines()
        if line and not line.startswith('#')
    ]

with open(path.join(here, 'requirements.dev.txt'), encoding='utf-8') as f:
    requirements_dev = [
        line for line in f.readlines()
        if line and not line.startswith('#')
    ]


setup(
    name='pik-django-utils',
    version='2.0.5',
    description='Common PIK Django utils and tools',
    # https://packaging.python.org/specifications/core-metadata/#description-optional
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/pik-software/pik-django-utils',
    author='pik-software',
    author_email='no-reply@pik-software.ru',
    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='pik django',

    packages=find_packages(exclude=['contrib', 'docs', 'tests']),

    # https://packaging.python.org/en/latest/requirements.html
    install_requires=requirements,
    python_requires='~=3.6',

    # List additional groups of dependencies here
    #   $ pip install sampleproject[dev]
    extras_require={
        'dev': requirements_dev,
    },

    # If there are data files included in your packages that need to be
    # installed, specify them here.
    #
    # If using Python 2.6 or earlier, then these have to be included in
    # MANIFEST.in as well.
    # package_data={  # Optional
    #     'sample': ['package_data.dat'],
    # },

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files
    #
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    # data_files=[('my_data', ['data/data_file'])],  # Optional

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # `pip` to create the appropriate form of executable for the target
    # platform.
    #
    # For example, the following would provide a command called `sample` which
    # executes the function `main` from this package when invoked:
    # entry_points={  # Optional
    #     'console_scripts': [
    #         'sample=sample:main',
    #     ],
    # },

    project_urls={
        'Bug Reports': 'https://github.com/pik-software/pik-django-utils/issues',
        'Funding': 'https://github.com/pik-software/pik-django-utils',
        'Say Thanks!': 'https://saythanks.io/to/pik_software',
        'Source': 'https://github.com/pik-software/pik-django-utils',
    },
)
