cmake_minimum_required(VERSION 3.20)
project(IWFM VERSION 2024.2 LANGUAGES C Fortran)

# Native Linux configuration reconstructed from IWFM 2024.2.1594 .vfproj files.
if(NOT UNIX)
  message(WARNING "This project was designed and tested on Linux. Windows builds should use DWR's .vfproj files.")
endif()

option(IWFM_BUILD_PREPROCESSOR "Build IWFM PreProcessor" ON)
option(IWFM_BUILD_SIMULATION "Build standard IWFM Simulation" ON)
option(IWFM_BUILD_PARALLEL "Build OpenMP Simulation_PLL" ON)
option(IWFM_BUILD_BUDGET "Build Budget" ON)
option(IWFM_BUILD_ZBUDGET "Build ZBudget" ON)
option(IWFM_BUILD_MM "Build experimental coarray Simulation_MM" OFF)
option(IWFM_BUILD_SHARED "Build experimental C-exports shared library" OFF)

set(IWFM_HECDSS_LIBRARY "" CACHE FILEPATH "Full path to native Linux HEC-DSS libheclib.so or libheclib.a")
set(IWFM_HECDSS_LIBRARY_DIR "" CACHE PATH "Optional directory containing libheclib")
set(IWFM_HECDSS_EXTRA_LIBRARIES "" CACHE STRING "Optional extra libraries for static HEC-DSS, e.g. gfortran;quadmath")

# Enable for external Fortran 'INCLUDE' files, and native preprocessor conditionals.
set(CMAKE_Fortran_PREPROCESS ON)
set(CMAKE_Fortran_MODULE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/modules")

find_package(HDF5 REQUIRED COMPONENTS C Fortran)
find_package(Threads REQUIRED)
find_package(ZLIB REQUIRED)
if(NOT IWFM_HECDSS_LIBRARY)
  find_library(IWFM_HECDSS_LIBRARY NAMES heclib heclib64
    HINTS "${IWFM_HECDSS_LIBRARY_DIR}"
    PATH_SUFFIXES lib lib64)
endif()
if(NOT IWFM_HECDSS_LIBRARY OR IWFM_HECDSS_LIBRARY MATCHES "-NOTFOUND$")
  message(FATAL_ERROR
    "Native Linux HEC-DSS library not found. Build heclib first, then configure with "
    "-DIWFM_HECDSS_LIBRARY=/absolute/path/to/libheclib.a (or .so). "
    "The bundled Windows .lib files are not usable on Linux.")
endif()
message(STATUS "Using HEC-DSS library: ${IWFM_HECDSS_LIBRARY}")
message(STATUS "Using HDF5 Fortran libraries: ${HDF5_Fortran_LIBRARIES}")

if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
  message(WARNING "IWFM 2024.2.1594 was released for Intel Fortran. Full GNU Fortran compilation is not yet supported; prefer ifx.")
endif()
include(cmake/IWFMSources.cmake)

if(IWFM_BUILD_PARALLEL)
  find_package(OpenMP REQUIRED COMPONENTS Fortran)
endif()

set(IWFM_OUTPUT_DIR "${CMAKE_BINARY_DIR}/bin" CACHE PATH "Directory for output binaries")
file(MAKE_DIRECTORY "${IWFM_OUTPUT_DIR}")

function(iwfm_add_program name source_list output_name)
  add_executable(${name} ${${source_list}})
  set_target_properties(${name} PROPERTIES
    OUTPUT_NAME "${output_name}"
    RUNTIME_OUTPUT_DIRECTORY "${IWFM_OUTPUT_DIR}"
    Fortran_MODULE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/mod/${name}")
  file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/mod/${name}")
  target_include_directories(${name} PRIVATE
    ${IWFM_FORTRAN_INCLUDE_DIRS}
    ${HDF5_INCLUDE_DIRS}
    ${HDF5_Fortran_INCLUDE_DIRS})
  target_link_libraries(${name} PRIVATE
    "${IWFM_HECDSS_LIBRARY}"
    ${HDF5_Fortran_LIBRARIES}
    ${HDF5_C_LIBRARIES}
    ZLIB::ZLIB Threads::Threads ${CMAKE_DL_LIBS} ${IWFM_HECDSS_EXTRA_LIBRARIES})
  if(UNIX)
    target_link_libraries(${name} PRIVATE m)
  endif()
  # The Windows project sets /fp:consistent /assume:norealloc_lhs.
  if(CMAKE_Fortran_COMPILER_ID MATCHES "Intel")
    target_compile_options(${name} PRIVATE
      $<$<COMPILE_LANGUAGE:Fortran>:-fpp>
      $<$<COMPILE_LANGUAGE:Fortran>:-assume>
      $<$<COMPILE_LANGUAGE:Fortran>:norealloc_lhs>
      $<$<COMPILE_LANGUAGE:Fortran>:-fp-model=consistent>)
    target_compile_options(${name} PRIVATE
      $<$<CONFIG:Debug>:-traceback>
      $<$<CONFIG:Debug>:-check>
      $<$<CONFIG:Debug>:bounds>)
  elseif(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
    # Best-effort GNU port; Intel ifx is closer to the official build.
    target_compile_options(${name} PRIVATE
      $<$<COMPILE_LANGUAGE:Fortran>:-cpp>
      $<$<COMPILE_LANGUAGE:Fortran>:-ffree-line-length-none>
      $<$<COMPILE_LANGUAGE:Fortran>:-fallow-argument-mismatch>
      $<$<COMPILE_LANGUAGE:Fortran>:-fno-realloc-lhs>)
    target_compile_options(${name} PRIVATE
      $<$<CONFIG:Debug>:-g>
      $<$<CONFIG:Debug>:-fcheck=bounds>
      $<$<CONFIG:Debug>:-fbacktrace>)
  else()
    message(WARNING "Compiler ${CMAKE_Fortran_COMPILER_ID} is not tested with IWFM")
  endif()
endfunction()

if(IWFM_BUILD_PREPROCESSOR)
  iwfm_add_program(PreProcessor IWFM_SOURCES_PreProcessor PreProcessor)
endif()
if(IWFM_BUILD_SIMULATION)
  iwfm_add_program(Simulation IWFM_SOURCES_Simulation Simulation)
endif()
if(IWFM_BUILD_PARALLEL)
  iwfm_add_program(Simulation_PLL IWFM_SOURCES_Simulation_Parallel Simulation_PLL)
  target_link_libraries(Simulation_PLL PRIVATE OpenMP::OpenMP_Fortran)
endif()
if(IWFM_BUILD_BUDGET)
  iwfm_add_program(Budget IWFM_SOURCES_Budget Budget)
endif()
if(IWFM_BUILD_ZBUDGET)
  iwfm_add_program(ZBudget IWFM_SOURCES_ZBudget ZBudget)
endif()
if(IWFM_BUILD_MM)
  iwfm_add_program(Simulation_MM IWFM_SOURCES_Simulation_MM Simulation_MM)
  if(CMAKE_Fortran_COMPILER_ID MATCHES "Intel")
    target_compile_options(Simulation_MM PRIVATE -coarray=shared -coarray-num-images=10)
    target_link_options(Simulation_MM PRIVATE -coarray=shared -coarray-num-images=10)
  elseif(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
    target_compile_options(Simulation_MM PRIVATE -fcoarray=single)
    target_link_options(Simulation_MM PRIVATE -fcoarray=single)
    message(WARNING "GNU -fcoarray=single only runs one image; not equivalent to the 10-image Intel build.")
  endif()
endif()
if(IWFM_BUILD_SHARED)
  # Windows !DEC$ STDCALL/DLLEXPORT attributes are NOT a portable C ABI.
  # This target can be compiled, but symbols/interfaces require independent validation.
  add_library(IWFM_C SHARED ${IWFM_SOURCES_IWFM_C})
  set_target_properties(IWFM_C PROPERTIES
    OUTPUT_NAME "IWFM_C"
    LIBRARY_OUTPUT_DIRECTORY "${IWFM_OUTPUT_DIR}"
    Fortran_MODULE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/mod/IWFM_C")
  file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/mod/IWFM_C")
  target_include_directories(IWFM_C PRIVATE ${IWFM_FORTRAN_INCLUDE_DIRS} ${HDF5_INCLUDE_DIRS} ${HDF5_Fortran_INCLUDE_DIRS})
  target_link_libraries(IWFM_C PRIVATE "${IWFM_HECDSS_LIBRARY}" ${HDF5_Fortran_LIBRARIES} ${HDF5_C_LIBRARIES} ZLIB::ZLIB Threads::Threads ${CMAKE_DL_LIBS} ${IWFM_HECDSS_EXTRA_LIBRARIES})
  if(UNIX)
    target_link_libraries(IWFM_C PRIVATE m)
  endif()
  set_target_properties(IWFM_C PROPERTIES POSITION_INDEPENDENT_CODE ON)
  if(CMAKE_Fortran_COMPILER_ID MATCHES "Intel")
    target_compile_options(IWFM_C PRIVATE -fpp -heap-arrays 900)
  elseif(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
    target_compile_options(IWFM_C PRIVATE -cpp -ffree-line-length-none -fallow-argument-mismatch -fno-realloc-lhs)
  endif()
  message(WARNING "IWFM_C Linux exports are experimental; DWR's Windows STDCALL interface is not preserved automatically.")
endif()
