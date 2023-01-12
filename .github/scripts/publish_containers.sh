#!/bin/bash

versions=("latest")
GIT_VERSION=$(git describe --tags --always --match 'v*')
if [ $1 == true ]; then
  XYZ_VERSION=${GIT_VERSION%-*-*}
  XY_VERSION=${XYZ_VERSION%.*}
  X_VERSION=${XY_VERSION%.*}
  versions+=(${X_VERSION}, ${XY_VERSION}, ${XYZ_VERSION})
fi
versions+=(${GIT_VERSION})

for version in "${versions[@]}"; do
  docker tag topo-imagery-test ghcr.io/paulfouquet/topo-imagery-test:$version
  docker push ghcr.io/paulfouquet/topo-imagery-test:$version
done