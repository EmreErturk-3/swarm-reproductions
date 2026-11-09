cmake_minimum_required(VERSION 3.16)
project(beeclust C CXX)

# Kilobot seconds per paper second; see README.md, "Time scale".
set(BEECLUST_TIME_SCALE "" CACHE STRING "Kilobot seconds per paper second")
if(NOT BEECLUST_TIME_SCALE)
  message(FATAL_ERROR "Configure with -DBEECLUST_TIME_SCALE=<k>")
endif()
set(BEECLUST_CONTACT_DISTANCE_MM 52 CACHE STRING "Message distance counted as contact [mm]")

# ARGoS installs a CMake package configuration (found through CMAKE_PREFIX_PATH,
# see scripts/env.sh). It looks for its helper modules under CMAKE_INSTALL_PREFIX,
# so their location is given explicitly for installations elsewhere.
find_path(ARGOS_CMAKE_DIR ARGoSConfig.cmake
  HINTS $ENV{ARGOS_PREFIX}/share/argos3/cmake /usr/local/share/argos3/cmake /usr/share/argos3/cmake)
find_package(ARGoS REQUIRED)
find_path(KILOLIB_INCLUDE_DIR kilolib.h
  PATH_SUFFIXES argos3/plugins/robots/kilobot/control_interface REQUIRED)

include_directories(${ARGOS_INCLUDE_DIRS} ${KILOLIB_INCLUDE_DIR} src)
link_directories(${ARGOS_LIBRARY_DIR})

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# Kilobot controller: one process per simulated robot.
add_executable(beeclust src/beeclust.c)
target_compile_definitions(beeclust PRIVATE
  BEECLUST_TIME_SCALE=${BEECLUST_TIME_SCALE}
  CONTACT_DISTANCE_MM=${BEECLUST_CONTACT_DISTANCE_MM})
target_link_libraries(beeclust argos3plugin_simulator_kilolib m)

# Environment: virtual sensors, measurements, floor colouring.
add_library(beeclust_loop_functions MODULE src/beeclust_loop_functions.cpp)
target_compile_features(beeclust_loop_functions PRIVATE cxx_std_17)
target_link_libraries(beeclust_loop_functions
  argos3core_simulator
  argos3plugin_simulator_entities
  argos3plugin_simulator_kilobot)
