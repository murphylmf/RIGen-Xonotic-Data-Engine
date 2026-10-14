#!/usr/bin/env bash
[ -z "$QCCFLAGS_WATERMARK" ] && export QCCFLAGS_WATERMARK=$(git describe --tags --dirty='~')
set -eu
cd ${0%/*}








if [ -f ../../csprogs.dat ]; then
    rm ../../csprogs.dat
fi

if [ -f ../../menu.dat ]; then
    rm ../../menu.dat
fi

if [ -f ../../progs.dat ]; then
    rm ../../progs.dat
fi

WORKDIR=../.tmp

CPP="cc -xc -E"
: ${QCC:=$PWD/../../../../gmqcc/gmqcc}

declare -a QCCDEFS=(
    -DNDEBUG=1
    -DXONOTIC=1
    -DWATERMARK="\"$QCCFLAGS_WATERMARK\""
    -DENABLE_EFFECTINFO=0
    -DENABLE_DEBUGDRAW=0
    -DENABLE_DEBUGTRACE=0
)
QCCDEFS="${QCCDEFS[@]}"

declare -a QCCFLAGS=(
    -std=gmqcc




    -O3
    -Wall -Werror
    -futf8
    -freturn-assignments
    -frelaxed-switch
    -Ooverlap-locals
)
declare -a NOWARN=(
    -Wno-field-redeclared
    -Wno-unused-variable
    -Wno-implicit-function-pointer
    -Wno-missing-return-values
)
QCCFLAGS="${QCCFLAGS[@]} ${NOWARN[@]}"

. qcc.sh
cd ..

function check1() {
    declare -l prog="${1}"
    declare -l file="${2}"
    MODE=${prog}
    includes="-include lib/_all.inc"
    [ -f ${prog}/_all.qh ] && includes="${includes} -include ${prog}/_all.qh"
    qpp ${file} test-${prog}.dat \
            ${includes} \
            -I. ${QCCIDENT} ${QCCDEFS} > ${WORKDIR}/${prog}.qc
    qcc ${QCCFLAGS} -o ../${WORKDIR}/test-${prog}.dat ../${WORKDIR}/${prog}.qc >/dev/null
}

function check() {
    declare -l prog="${1}"
    find ${prog} -type f -name '*.qc' -print0 | sort -z | while read -r -d '' file; do
        check1 ${prog} ${file}
    done
}

if [ ${#@} -eq 0 ]; then
    check client
    check server
    check menu
else
    for var in ${@}; do
        var=${var#test-}
        check ${var}
    done
fi
