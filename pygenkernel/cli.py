# Copyright (C) 2012 Gentoo Foundation
# Written by Sebastian Pipping <sebastian@pipping.org>
# Licensed under GPL v2 or later

from __future__ import print_function

import sys
import subprocess
import copy
import os
try:
	import argparse
except ImportError:
	print('ERROR: Either >=dev-lang/python-2.7 or dev-python/argparse is required', file=sys.stderr)
	sys.exit(1)


_VERSION = '3.4.41'

_SPLASH_THEME_UNSET = object()


def parse_command_line():
	parser = argparse.ArgumentParser('genkernel',
			description='Gentoo Linux Genkernel %s' % _VERSION,
			version=_VERSION)

	group_conf = parser.add_argument_group('Configuration settings')
	group_conf.add_argument('--config', metavar='FILE', dest='CMD_GK_CONFIG', help='genkernel configuration file to use')

	group_debug = parser.add_argument_group('Debug settings')
	group_debug.add_argument('--loglevel', metavar='INT', dest='CMD_DMRAID', type=int, help='Debug Verbosity Level (0-5)')
	group_debug.add_argument('--logfile', metavar='FILE', dest='CMD_LOGFILE', help='Output file for debug info')
	group_debug.add_argument('--color', action='store_true', dest='USECOLOR', help='Output debug in color')
	group_debug.add_argument('--no-color', action='store_false', dest='USECOLOR', help='Do not output debug in color')

	group_kernel_conf = parser.add_argument_group('Kernel Configuration settings')
	group_kernel_conf.add_argument('--menuconfig', action='store_true', dest='CMD_MENUCONFIG', help='Run menuconfig after oldconfig')
	group_kernel_conf.add_argument('--no-menuconfig', action='store_false', dest='CMD_MENUCONFIG', help='Do not run menuconfig after oldconfig')
	group_kernel_conf.add_argument('--gconfig', action='store_true', dest='CMD_GCONFIG', help='Run gconfig after oldconfig')
	group_kernel_conf.add_argument('--no-gconfig', action='store_false', dest='CMD_GCONFIG', help='Don\'t run gconfig after oldconfig')
	group_kernel_conf.add_argument('--xconfig', action='store_true', dest='CMD_XCONFIG', help='Run xconfig after oldconfig')
	group_kernel_conf.add_argument('--no-xconfig', action='store_false', dest='CMD_XCONFIG', help='Don\'t run xconfig after oldconfig')
	group_kernel_conf.add_argument('--save-config', action='store_true', dest='CMD_SAVE_CONFIG', help='Save the configuration to /etc/kernels')
	group_kernel_conf.add_argument('--no-save-config', action='store_false', dest='CMD_SAVE_CONFIG', help='Don\'t save the configuration to /etc/kernels')

	group_kernel_compile = parser.add_argument_group('Kernel Compile settings')
	group_kernel_compile.add_argument('--oldconfig', action='store_true', dest='CMD_OLDCONFIG', help='Implies --no-clean and runs a "make oldconfig"')
	group_kernel_compile.add_argument('--no-oldconfig', action='store_false', dest='CMD_OLDCONFIG', help='Do not run "make oldconfig"')
	group_kernel_compile.add_argument('--clean', action='store_true', dest='CMD_CLEAN', help='Run make clean before compilation')
	group_kernel_compile.add_argument('--no-clean', action='store_false', dest='CMD_CLEAN', help='Do not run "make clean"')
	group_kernel_compile.add_argument('--mrproper', action='store_true', dest='CMD_MRPROPER', help='Run make mrproper before compilation')
	group_kernel_compile.add_argument('--no-mrproper', action='store_false', dest='CMD_MRPROPER', help='Do not run make mrproper before compilation')
	group_kernel_compile.add_argument('--install', action='store_true', dest='CMD_INSTALL', help='Install the kernel after building')
	group_kernel_compile.add_argument('--no-install', action='store_false', dest='CMD_INSTALL', help='Do not install the kernel after building')
	group_kernel_compile.add_argument('--symlink', action='store_true', dest='CMD_SYMLINK', help='Manage symlinks in /boot for installed images')
	group_kernel_compile.add_argument('--no-symlink', action='store_false', dest='CMD_SYMLINK', help='Do not manage symlinks')
	group_kernel_compile.add_argument('--ramdisk-modules', action='store_true', dest='CMD_RAMDISKMODULES', help='Copy required modules to the ramdisk')
	group_kernel_compile.add_argument('--no-ramdisk-modules', action='store_false', dest='CMD_RAMDISKMODULES', help='Don\'t copy any modules to the ramdisk')
	group_kernel_compile.add_argument('--all-ramdisk-modules', action='store_true', dest='CMD_ALLRAMDISKMODULES', help='Copy all kernel modules to the ramdisk')
	group_kernel_compile.add_argument('--no-all-ramdisk-modules', action='store_false', dest='CMD_ALLRAMDISKMODULES', help='Do not copy all kernel modules to the ramdisk')
	group_kernel_compile.add_argument('--callback', metavar='COMMAND', dest='CMD_CALLBACK', help='Run the specified arguments after the kernel and modules have been compiled')
	group_kernel_compile.add_argument('--static', action='store_true', dest='CMD_STATIC', help='Build a static (monolithic) kernel')
	group_kernel_compile.add_argument('--no-static', action='store_false', dest='CMD_STATIC', help='Do not build a static (monolithic) kernel')

	group_kernel_conf = parser.add_argument_group('Kernel settings')
	group_kernel_conf.add_argument('--kerneldir', metavar='DIR', dest='CMD_KERNEL_DIR', help='Location of the kernel sources')
	group_kernel_conf.add_argument('--kernel-config', metavar='FILE', dest='CMD_KERNEL_CONFIG', help='Kernel configuration file to use for compilation')
	group_kernel_conf.add_argument('--module-prefix', metavar='DIR', dest='CMD_INSTALL_MOD_PATH', help='Prefix to kernel module destination, modules will be installed in <prefix>/lib/modules')

	group_low_level = parser.add_argument_group('Low-Level Compile settings')
	group_low_level.add_argument('--kernel-cc', metavar='COMPILER', dest='CMD_KERNEL_CC', help='Compiler to use for kernel (e.g. distcc)')
	group_low_level.add_argument('--kernel-as', metavar='ASSEMBLER', dest='CMD_KERNEL_AS', help='Assembler to use for kernel')
	group_low_level.add_argument('--kernel-ld', metavar='LINKER', dest='CMD_KERNEL_LD', help='Linker to use for kernel')
	group_low_level.add_argument('--kernel-cross-compile', metavar='COMMAND', dest='CMD_KERNEL_CROSS_COMPILE', help='CROSS_COMPILE kernel variable')
	group_low_level.add_argument('--kernel-make', metavar='MAKEPRG', dest='CMD_KERNEL_MAKE', help='GNU Make to use for kernel')
	group_low_level.add_argument('--kernel-target', metavar='TARGET', dest='KERNEL_MAKE_DIRECTIVE_OVERRIDE', help='Override default make target (bzImage)')
	group_low_level.add_argument('--kernel-binary', metavar='PATH', dest='KERNEL_BINARY_OVERRIDE', help='Override default kernel binary path (arch/foo/boot/bar)')
	group_low_level.add_argument('--utils-cc', metavar='COMPILER', dest='CMD_UTILS_CC', help='Compiler to use for utilities')
	group_low_level.add_argument('--utils-as', metavar='ASSEMBLER', dest='CMD_UTILS_AS', help='Assembler to use for utils')
	group_low_level.add_argument('--utils-ld', metavar='LINKER', dest='CMD_UTILS_LD', help='Linker to use for utils')
	group_low_level.add_argument('--utils-make', metavar='MAKEPRG', dest='CMD_UTILS_MAKE', help='GNU Make to use for utils')
	group_low_level.add_argument('--utils-cross-compile', metavar='COMMAND', dest='CMD_UTILS_CROSS_COMPILE', help='CROSS_COMPILE utils variable')
	group_low_level.add_argument('--utils-arch', metavar='ARCH', dest='CMD_UTILS_ARCH', help='Force to arch for utils only instead of autodetect')
	group_low_level.add_argument('--makeopts', metavar='OPTIONS', dest='CMD_MAKEOPTS', help='Make options such as -j2, etc...')
	group_low_level.add_argument('--mountboot', action='store_true', dest='CMD_MOUNTBOOT', help='Mount BOOTDIR automatically if mountable')
	group_low_level.add_argument('--no-mountboot', action='store_false', dest='CMD_MOUNTBOOT', help='Don\'t mount BOOTDIR automatically')
	group_low_level.add_argument('--bootdir', metavar='DIR', dest='CMD_BOOTDIR', help='Set the location of the boot-directory, default is /boot')
	group_low_level.add_argument('--modprobedir', metavar='DIR', dest='CMD_MODPROBEDIR', help='Set the location of the modprobe.d-directory, default is /etc/modprobe.d')

	group_init = parser.add_argument_group('Initialization')
	group_init.add_argument('--splash', nargs='?', metavar='THEME', dest='SPLASH_THEME', default=_SPLASH_THEME_UNSET, help='Enable framebuffer splash (using THEME)')
	group_init.add_argument('--no-splash', action='store_false', dest='CMD_SPLASH', help='Do not install framebuffer splash')
	group_init.add_argument('--splash-res', metavar='RES', dest='SPLASH_RES', help='Select splash theme resolutions to install')
	group_init.add_argument('--gensplash', nargs='?', metavar='THEME', dest='SPLASH_THEME', default=_SPLASH_THEME_UNSET, help='Deprecated, use --splash')
	group_init.add_argument('--no-gensplash', action='store_false', dest='CMD_SPLASH', help='Deprecated, use --no-splash')
	group_init.add_argument('--gensplash-res', metavar='RES', dest='SPLASH_RES', help='Deprecated, use --splash-res')
	group_init.add_argument('--do-keymap-auto', action='store_true', dest='CMD_DOKEYMAPAUTO', help='Forces keymap selection at boot')
	group_init.add_argument('--keymap', action='store_true', dest='CMD_KEYMAP', help='Enables keymap selection support')
	group_init.add_argument('--no-keymap', action='store_false', dest='CMD_KEYMAP', help='Disables keymap selection support')
	group_init.add_argument('--lvm', action='store_true', dest='CMD_LVM', help='Include LVM support')
	group_init.add_argument('--no-lvm', action='store_false', dest='CMD_LVM', help='Exclude LVM support')
	group_init.add_argument('--lvm2', action='store_true', dest='CMD_LVM', help='Include LVM support (deprecated, use --lvm)')
	group_init.add_argument('--no-lvm2', action='store_false', dest='CMD_LVM', help='Exclude LVM support (deprecated, use --no-lvm)')
	group_init.add_argument('--mdadm', action='store_true', dest='CMD_MDADM', help='Include MDADM/MDMON support')
	group_init.add_argument('--no-mdadm', action='store_false', dest='CMD_MDADM', help='Exclude MDADM/MDMON support')
	group_init.add_argument('--mdadm-config', metavar='FILE', dest='CMD_MDADM_CONFIG', help='Use file as mdadm.conf in initramfs')
	group_init.add_argument('--dmraid', action='store_true', dest='CMD_NETBOOT', help='Include DMRAID support')
	group_init.add_argument('--no-dmraid', action='store_false', dest='CMD_NETBOOT', help='Exclude DMRAID support')
	group_init.add_argument('--zfs', action='store_true', dest='CMD_ZFS', help='Include ZFS support')
	group_init.add_argument('--no-zfs', action='store_false', dest='CMD_ZFS', help='Exclude ZFS support')
	group_init.add_argument('--multipath', action='store_true', dest='CMD_MULTIPATH', help='Include Multipath support')
	group_init.add_argument('--no-multipath', action='store_false', dest='CMD_MULTIPATH', help='Exclude Multipath support')
	group_init.add_argument('--iscsi', action='store_true', dest='CMD_ISCSI', help='Include iSCSI support')
	group_init.add_argument('--no-iscsi', action='store_false', dest='CMD_ISCSI', help='Exclude iSCSI support')
	group_init.add_argument('--bootloader', choices=('grub', ), dest='CMD_BOOTLOADER', help='Add new kernel to GRUB configuration')
	group_init.add_argument('--linuxrc', metavar='FILE', dest='CMD_LINUXRC', help='Specifies a user created linuxrc')
	group_init.add_argument('--busybox-config', metavar='FILE', dest='CMD_BUSYBOX_CONFIG', help='Specifies a user created busybox config')
	group_init.add_argument('--genzimage', action='store_true', dest='CMD_GENZIMAGE', help='Make and install kernelz image (PowerPC)')
	group_init.add_argument('--disklabel', action='store_true', dest='CMD_DISKLABEL', help='Include disk label and uuid support in your ramdisk')
	group_init.add_argument('--no-disklabel', action='store_false', dest='CMD_DISKLABEL', help='Exclude disk label and uuid support from your ramdisk')
	group_init.add_argument('--luks', action='store_true', dest='CMD_LUKS', help='Include LUKS support')
	group_init.add_argument('--no-luks', action='store_false', dest='CMD_LUKS', help='Exclude LUKS support')
	group_init.add_argument('--gpg', action='store_true', dest='CMD_GPG', help='Include GPG-armored LUKS key support')
	group_init.add_argument('--no-gpg', action='store_false', dest='CMD_GPG', help='Exclude GPG-armored LUKS key support')
	group_init.add_argument('--busybox', action='store_true', dest='CMD_BUSYBOX', help='Include busybox')
	group_init.add_argument('--no-busybox', action='store_false', dest='CMD_BUSYBOX', help='Exclude busybox')
	group_init.add_argument('--unionfs', action='store_true', dest='CMD_UNIONFS', help='Include support for unionfs')
	group_init.add_argument('--no-unionfs', action='store_false', dest='CMD_UNIONFS', help='Exclude support for unionfs')
	group_init.add_argument('--netboot', action='store_true', dest='CMD_NETBOOT', help='Create a self-contained env in the initramfs')
	group_init.add_argument('--no-netboot', action='store_false', dest='CMD_NETBOOT', help='Exclude --netboot env')
	group_init.add_argument('--real-root', metavar='DEVICE', dest='CMD_REAL_ROOT', help='Specify a default for real_root=')

	group_internals = parser.add_argument_group('Internals')
	group_internals.add_argument('--arch-override', metavar='ARCH', dest='CMD_ARCHOVERRIDE', help='Force to arch instead of autodetect')
	group_internals.add_argument('--cachedir', metavar='DIR', dest='CACHE_DIR', help='Override the default cache location')
	group_internals.add_argument('--tempdir', metavar='DIR', dest='TMPDIR', help='Location of Genkernel\'s temporary directory')
	group_internals.add_argument('--postclear', action='store_true', dest='CMD_POSTCLEAR', help='Clear all tmp files and caches after genkernel has run')
	group_internals.add_argument('--no-postclear', action='store_false', dest='CMD_POSTCLEAR', help='Do not clean up after genkernel has run')

	group_output = parser.add_argument_group('Output Settings')
	group_output.add_argument('--kernname', metavar='LABEL', dest='KERNNAME', help='Tag the kernel and ramdisk with a name: If not defined the option defaults to "genkernel"')
	group_output.add_argument('--minkernpackage', metavar='FILE', dest='MINKERNPACKAGE', help='File to output a .tar.bz2\'d kernel and ramdisk: No modules outside of the ramdisk will be included...')
	group_output.add_argument('--modulespackage', metavar='FILE', dest='MODULESPACKAGE', help='File to output a .tar.bz2\'d modules after the callbacks have run')
	group_output.add_argument('--kerncache', metavar='FILE', dest='KERNCACHE', help='File to output a .tar.bz2\'d kernel contents of /lib/modules/ and the kernel config. NOTE: This is created before the callbacks are run!')
	group_output.add_argument('--no-kernel-sources', action='store_false', dest='CMD_KERNEL_SOURCES', help='This option is only valid if kerncache is defined. If there is a valid kerncache no checks will be made against a kernel source tree')
	group_output.add_argument('--kernel-sources', action='store_true', dest='CMD_KERNEL_SOURCES', help='Revert --no-kernel-sources')
	group_output.add_argument('--initramfs-overlay', metavar='DIR', dest='CMD_INITRAMFS_OVERLAY', help='Directory structure to include in the initramfs, only available on 2.6 kernels')
	group_output.add_argument('--firmware', action='store_true', dest='CMD_FIRMWARE', help='Enable copying of firmware into initramfs')
	group_output.add_argument('--no-firmware', action='store_false', dest='CMD_FIRMWARE', help='Disable copying of firmware into initramfs')
	group_output.add_argument('--firmware-dir', metavar='DIR', dest='CMD_FIRMWARE_DIR', help='Specify directory to copy firmware from (defaults to /lib/firmware)')
	group_output.add_argument('--firmware-files', metavar='FILE[,FILE,..]', dest='CMD_FIRMWARE_FILES', help='Specifies specific firmware files to copy. This overrides --firmware-dir. For multiple files, separate the filenames with a comma')
	group_output.add_argument('--integrated-initramfs', action='store_true', dest='CMD_INTEGRATED_INITRAMFS', help='Include the generated initramfs in the kernel instead of keeping it as a separate file')
	group_output.add_argument('--no-integrated-initramfs', action='store_false', dest='CMD_INTEGRATED_INITRAMFS', help='Exclude the generated initramfs from the kernel, keep it as a separate file')
	group_output.add_argument('--compress-initramfs', action='store_true', dest='CMD_COMPRESS_INITRD', help='Compress the generated initramfs')
	group_output.add_argument('--compress-initrd', action='store_true', dest='CMD_COMPRESS_INITRD', help='Compress the generated initramfs')
	group_output.add_argument('--no-compress-initramfs', action='store_false', dest='CMD_COMPRESS_INITRD', help='Do not compress the generated initramfs')
	group_output.add_argument('--no-compress-initrd', action='store_false', dest='CMD_COMPRESS_INITRD', help='Do not compress the generated initramfs')
	group_output.add_argument('--compress-initramfs-type', choices=('best', 'xz', 'lzma', 'bzip2', 'gzip', 'lzop'), dest='CMD_COMPRESS_INITRD_TYPE', help='Compression type for initramfs')
	group_output.add_argument('--compress-initrd-type', choices=('best', 'xz', 'lzma', 'bzip2', 'gzip', 'lzop'), dest='CMD_COMPRESS_INITRD_TYPE', help='Compression type for initramfs')

	parser.add_argument('target', choices=('all', 'initramfs', 'ramdisk', 'kernel', 'bzImage'), help='What to build')

	options = parser.parse_args()

	if options.SPLASH_THEME is _SPLASH_THEME_UNSET:
		options.SPLASH_THEME = None
	elif options.SPLASH_THEME is None:
		options.CMD_SPLASH = True

	return options


def _find_geninitramfs(argv_null):
	genkernel_bin_folder = os.path.dirname(argv_null)
	return os.path.join(genkernel_bin_folder, 'geninitramfs')


def main():
	geninitramfs_bin_location = _find_geninitramfs(sys.argv[0])
	geninitramfs_argv = [geninitramfs_bin_location] + sys.argv[1:]

	# For now just...
	# - limit to valid parameters
	# - show our one --help and --version
	_ = parse_command_line()

	# Forward to geninitramfs
	p = subprocess.Popen(geninitramfs_argv)
	p.wait()
	sys.exit(p.returncode)
