#!/bin/bash

GIT_VERSION="v.0.4.0"
XYZ_VERSION=${GIT_VERSION%-*-*}
XY_VERSION=${XYZ_VERSION%.*}
X_VERSION=${XY_VERSION%.*}

for version in "latest" ${X_VERSION} ${XY_VERSION} ${XYZ_VERSION} ${GIT_VERSION}; do
  docker tag topo-imagery-test ghcr.io/paulfouquet/topo-imagery-test:$version
  docker push ghcr.io/paulfouquet/topo-imagery-test:$version
done