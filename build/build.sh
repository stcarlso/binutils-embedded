#!/bin/bash

# Run in subdirectory
../configure --prefix=/opt/avr --target=avr --disable-libquadmath --disable-libstdcxx --enable-lto --disable-gold --disable-gprofng --disable-libssp --disable-libada --disable-intl --disable-tests --disable-doc --disable-nls --disable-werror
# make && make install-strip
