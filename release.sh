#!/bin/bash

set -e

git checkout master
git pull

die() { echo "$*" 1>&2 ; exit 1; }

python -m pip install "pip>=9.0.3"
python -m pip install "setuptools>=39.0.1"
python -m pip install "twine>=1.11.0"
python -m pip install "wheel>=0.30.0"
python -m pip install "pygments>=2.2.0"

VERSION=$(python setup.py --version)
NAME=$(python setup.py --name)

LAST_VERSION=$(git describe --tags --abbrev=0 --match v*)
LAST_VERSION=${LAST_VERSION:1}

if [[ ${LAST_VERSION} == ${VERSION} ]]; then
	die "You should update release VERSION"
fi

echo "PACKAGE: $NAME"
echo "CURRENT VERSION: $LAST_VERSION"
echo "NEW VERSION: $VERSION"

#python setup.py build
python setup.py sdist
python -m twine upload dist/${NAME}-${VERSION}.tar.gz
git tag -a v$VERSION -m "version $VERSION"
git push --tags
git push origin master
