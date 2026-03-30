# Maintainer: Egor Kurochkin <itsegork@gmail.com>
pkgname=shellix
pkgver=1.0.1
pkgrel=1
pkgdesc="Virtual terminal for Linux with tab support and customizable options"
arch=('any')
url="https://github.com/itsegork/shellix"
license=('MIT')
depends=(
    'python'
    'python-gobject'
    'python-requests'
    'gtk4'
    'libadwaita'
    'vte4'
    'python-psutil'
    'cairo'
    'pango'
    'ttf-jetbrains-mono-nerd'
)
makedepends=()
source=()
sha256sums=()

package() {
    cd "$srcdir/.."
    
    install -dm755 "$pkgdir/usr/share/$pkgname"
    install -dm755 "$pkgdir/usr/bin"
    install -dm755 "$pkgdir/usr/share/applications"
    install -dm755 "$pkgdir/usr/share/pixmaps"
    
    cp -r src "$pkgdir/usr/share/$pkgname/"
    
    if [ -d data ]; then
        cp -r data "$pkgdir/usr/share/$pkgname/"
    fi
    
    if [ -f LICENSE ]; then
        cp LICENSE "$pkgdir/usr/share/$pkgname/"
    fi
    
    cp *.py "$pkgdir/usr/share/$pkgname/" 2>/dev/null || true
    
    cat > "$pkgdir/usr/bin/$pkgname" << EOF

#!/bin/bash
cd /usr/share/$pkgname
exec python3 src/main.py
EOF
    chmod +x "$pkgdir/usr/bin/$pkgname"
    
    if [ -f "$pkgdir/usr/share/$pkgname/data/icons/ru.itsegork.shellix.svg" ]; then
        cp "$pkgdir/usr/share/$pkgname/data/icons/ru.itsegork.shellix.svg" \
           "$pkgdir/usr/share/pixmaps/$pkgname.svg"
    fi
    
    cat > "$pkgdir/usr/share/applications/$pkgname.desktop" << EOF
[Desktop Entry]
Name=Shellix
Comment=Virtual terminal for Linux with tab support and customizable options
Exec=$pkgname
Icon=$pkgname
Terminal=false
Type=Application
Categories=Development;System;
Keywords=console;terminal;manager;shell;vte;
EOF
}