cmake_minimum_required(VERSION 3.22.1)
project(canonraw LANGUAGES CXX)
include(FetchContent)
FetchContent_Declare(libraw_source
    URL https://www.libraw.org/data/LibRaw-0.22.2.zip
    URL_HASH SHA256=f4448371523f9960d26a131ed9dc21bee49f967adbcc4fb6f56b9b47c2ba87c6)
FetchContent_GetProperties(libraw_source)
if(NOT libraw_source_POPULATED)
    FetchContent_Populate(libraw_source)
endif()
file(GLOB_RECURSE LIBRAW_SOURCES CONFIGURE_DEPENDS "${libraw_source_SOURCE_DIR}/src/*.cpp")
# The *_ph.cpp files are alternative placeholders, not library translation units.
list(FILTER LIBRAW_SOURCES EXCLUDE REGEX "_ph\\.cpp$")
add_library(canonraw SHARED raw_decoder.cpp ${LIBRAW_SOURCES})
target_include_directories(canonraw PRIVATE "${libraw_source_SOURCE_DIR}")
target_compile_features(canonraw PRIVATE cxx_std_17)
target_compile_definitions(canonraw PRIVATE LIBRAW_NODLL USE_ZLIB)
target_compile_options(canonraw PRIVATE -fexceptions -fvisibility=hidden)
target_link_libraries(canonraw PRIVATE z)
