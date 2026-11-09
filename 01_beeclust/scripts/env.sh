# Source this file to use the ARGoS installation made by install_argos.sh.
export ARGOS_PREFIX="${ARGOS_PREFIX:-$HOME/.local/opt/argos3}"
export PATH="$ARGOS_PREFIX/bin:$PATH"
export LD_LIBRARY_PATH="$ARGOS_PREFIX/lib/argos3${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PKG_CONFIG_PATH="$ARGOS_PREFIX/lib/pkgconfig:$ARGOS_PREFIX/share/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
export ARGOS_PLUGIN_PATH="$ARGOS_PREFIX/lib/argos3${ARGOS_PLUGIN_PATH:+:$ARGOS_PLUGIN_PATH}"
export CMAKE_PREFIX_PATH="$ARGOS_PREFIX${CMAKE_PREFIX_PATH:+:$CMAKE_PREFIX_PATH}"
