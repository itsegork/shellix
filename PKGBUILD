# Maintainer: Egor Kurochkin <itsegork@gmail.com>
pkgname=shellix
pkgver=1.0.6
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
    'conspy'
    'nautilus-python'
)
makedepends=()
source=()
sha256sums=()

package() {
    local _projectroot="${startdir}"
    
    install -dm755 "${pkgdir}/usr/share/${pkgname}"
    install -dm755 "${pkgdir}/usr/bin"
    install -dm755 "${pkgdir}/usr/share/applications"
    install -dm755 "${pkgdir}/usr/share/nautilus-python/extensions"
    install -m644 "${_projectroot}/src/shellix_nautilus.py" \
        "${pkgdir}/usr/share/nautilus-python/extensions/shellix_nautilus.py"
    
    if [ -d "${_projectroot}/src" ]; then
        cp -r "${_projectroot}/src" "${pkgdir}/usr/share/${pkgname}/"
    else
        echo "Ошибка: Папка src не найдена в ${_projectroot}"
        return 1
    fi
    
    echo -e "#!/bin/bash\nexec python3 /usr/share/${pkgname}/src/main.py \"\$@\"" > "${pkgdir}/usr/bin/${pkgname}"
    chmod +x "${pkgdir}/usr/bin/${pkgname}"

    local icon_src="${_projectroot}/data/icons/ru.itsegork.shellix.svg"
    if [ -f "$icon_src" ]; then
        install -Dm644 "$icon_src" "${pkgdir}/usr/share/icons/hicolor/scalable/apps/ru.itsegork.shellix.svg"
        install -Dm644 "$icon_src" "${pkgdir}/usr/share/pixmaps/ru.itsegork.shellix.svg"
    fi

    cat > "${pkgdir}/usr/share/applications/ru.itsegork.shellix.desktop" << EOF
[Desktop Entry]
Name=Shellix
Comment=${pkgdesc}
Exec=${pkgname} %f
Icon=ru.itsegork.shellix
Terminal=false
Type=Application
Categories=Development;System;TerminalEmulator;
Keywords=console;terminal;manager;shell;vte;
StartupWMClass=Shellix
MimeType=inode/directory;
Actions=new-window;

[Desktop Action new-window]
Name=Open in Shellix
Exec=${pkgname} %f
EOF

    install -dm755 "${pkgdir}/usr/share/kio/servicemenus"
    cat > "${pkgdir}/usr/share/kio/servicemenus/ru.itsegork.shellix.desktop" << EOF
[Desktop Entry]
Type=Service
X-KDE-ServiceTypes=KonqPopupMenu/Plugin
MimeType=inode/directory;
Actions=openInShellix
X-KDE-Priority=TopLevel

[Desktop Action openInShellix]
Name=Open in Shellix
Icon=ru.itsegork.shellix
Exec=${pkgname} %f
EOF
}