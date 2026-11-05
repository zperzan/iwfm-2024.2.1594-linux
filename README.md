# Building IWFM 2024.2.1594 on Linux

Build IWFM with Intel `ifx`, HDF5 with Intel `ifx`/`icx`, and HEC-DSS with GCC/gfortran. These instructions assume the IWFM source tree (including its Linux CMake files and source patches) is available locally.

## Prerequisites

Intel oneAPI (`ifx`, `icx`), GCC/gfortran, CMake, GNU Make, Git, `wget`, and zlib development headers. Load the Intel environment:

```bash
source /opt/intel/oneapi/setvars.sh
```

Choose a working directory and run the remaining commands from there:

```bash
mkdir -p iwfm-build && cd iwfm-build
export DEPS_DIR="$PWD"
```

## 1. Build HEC-DSS

Use the `master` branch, which includes both C and Fortran sources:

```bash
git clone --branch master https://github.com/HydrologicEngineeringCenter/hec-dss.git
cd hec-dss/heclib
make clean
make CC="gcc -Wno-error=discarded-qualifiers -Wno-error=old-style-definition"

# Confirm that the required routines are present:
nm -g --defined-only Output/heclib.a | grep -Ei 'zopen_|zrrts_|zsrts_'
cd "$DEPS_DIR"
```

The build may fail at `javaHeclib` but the native archive can still be usable if it was built successfully. These instructions use the GCC/gfortran-compiled archive and link its Fortran runtime into IWFM.

## 2. Build minimal HDF5 1.14.6

```bash
wget https://github.com/HDFGroup/hdf5/releases/download/hdf5_1.14.6/hdf5-1.14.6.tar.gz
tar -xzf hdf5-1.14.6.tar.gz
export HDF5_PREFIX="$DEPS_DIR/hdf5-ifx"

cmake -S hdf5-1.14.6 -B hdf5-build -G "Unix Makefiles" \
    -DCMAKE_C_COMPILER=icx \
    -DCMAKE_Fortran_COMPILER=ifx \
    -DCMAKE_Fortran_FLAGS="-heap-arrays" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$HDF5_PREFIX" \
    -DHDF5_BUILD_FORTRAN=ON \
    -DHDF5_BUILD_HL_LIB=OFF \
    -DHDF5_BUILD_CPP_LIB=OFF \
    -DHDF5_BUILD_JAVA=OFF \
    -DHDF5_BUILD_TOOLS=OFF \
    -DHDF5_BUILD_EXAMPLES=OFF \
    -DBUILD_TESTING=OFF \
    -DHDF5_ENABLE_PARALLEL=OFF \
    -DHDF5_ENABLE_Z_LIB_SUPPORT=ON \
    -DHDF5_ENABLE_SZIP_SUPPORT=OFF \
    -DHDF5_ENABLE_PLUGIN_SUPPORT=OFF \
    -DBUILD_SHARED_LIBS=ON \
    -DBUILD_STATIC_LIBS=OFF

cmake --build hdf5-build --parallel 8
cmake --install hdf5-build
```

## 3. Build IWFM

Set `IWFM_SRC` to your local IWFM source directory (containing `CMakeLists.txt`):

```bash
export IWFM_SRC="/path/to/IWFM-2024.2.1594"
export HECLIB="$DEPS_DIR/hec-dss/heclib/Output/heclib.a"

for config in Release Debug; do
    if [ "$config" = Release ]; then out=build; else out=build-debug; fi
    cmake -S "$IWFM_SRC" -B "$IWFM_SRC/$out" -G "Unix Makefiles" \
        -DCMAKE_C_COMPILER=icx \
        -DCMAKE_Fortran_COMPILER=ifx \
        -DCMAKE_Fortran_FLAGS="-heap-arrays" \
        -DCMAKE_BUILD_TYPE="$config" \
        -DCMAKE_Fortran_FLAGS_DEBUG="-O0 -g -traceback -check bounds" \
        -DIWFM_HECDSS_LIBRARY="$HECLIB" \
        -DIWFM_HECDSS_EXTRA_LIBRARIES='gfortran;quadmath' \
        -DHDF5_ROOT="$HDF5_PREFIX" \
        -DCMAKE_PREFIX_PATH="$HDF5_PREFIX"
    cmake --build "$IWFM_SRC/$out" --parallel 8
done
```

Executables are placed in `build/bin/` (Release) and `build-debug/bin/` (Debug). When running them, the dynamic linker must be able to find the HDF5 shared libraries. If necessary, set `LD_LIBRARY_PATH="$HDF5_PREFIX/lib:${LD_LIBRARY_PATH:-}"`.

**Notes:** 
- The IWFM source files have been edited so Windows-style paths (e.g., using `\`) can be specified in an input file and they'll automatically ben converted to Linux-style paths. The same goes for CRLF lines.
- The `-heap-arrays` flag avoids large automatic arrays exhausting the default Linux stack.
