#!/bin/bash

# Run in subdirectory
../configure --prefix=/opt/arm-none-eabi --target=arm-none-eabi --disable-libquadmath --disable-libstdcxx --enable-lto --disable-gold --disable-gprofng --disable-libssp --disable-libada --disable-intl --disable-tests --disable-doc --disable-nls --enable-multilib --with-multilib-list=rmprofile
# make
