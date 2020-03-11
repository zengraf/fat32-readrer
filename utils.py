import colors


def lba(address):
    return address * 512


def split_directory_file(path):
    destination = path.rsplit('/', 1)
    if len(destination[0]) == 0:
        destination[0] = '/'
    elif len(destination) == 1:
        destination.insert(0, '')
    return destination


def split_paths(string):
    for i in range(len(string)):
        if string[i] == ' ' and not string[i - 1] == '\\':
            return string[0:i].strip(), string[i:].lstrip()
    return string.split(' ', 1)


def short_filename(long_filename, directory):
    long_filename = long_filename.rsplit('.', 1)
    filename = long_filename[0].replace('.', '').replace(' ', '_').replace('+', '').ljust(8, ' ')[0:8].upper()
    extension = long_filename[1].ljust(3, ' ')[0:3].upper() if len(long_filename) == 2 else "   "

    result = [entry for entry in directory.entries if
              filename[0:6] + '~' in entry.filename and entry.extension == extension]

    if long_filename[0].upper() != filename:
        if len(result) < 9:
            filename = (filename[0:6] + '~' + str(len(result) + 1)).replace(' ', '_')
        else:
            result = [entry for entry in directory.entries if
                      filename[0:5] + '~' in entry.filename and entry.extension == extension]
            filename = (filename[0:6] + '~' + str(len(result) + 10)).replace(' ', '_')

    return filename, extension


def print_mtod():
    print(colors.INFO,
          r"   ________  ________   _________   ________     _______         ",
          r"  |\  _____\|\   __  \ |\___   ___\|\_____  \   /  ___  \        ",
          r"  \ \  \__/ \ \  \|\  \\|___ \  \_|\|____|\ /_ /__/|_/  /|       ",
          r"   \ \   __\ \ \   __  \    \ \  \       \|\  \|__|//  / /       ",
          r"    \ \  \_|  \ \  \ \  \    \ \  \     __\_\  \   /  /_/__      ",
          r"     \ \__\    \ \__\ \__\    \ \__\   |\_______\ |\________\    ",
          r"      \|__|     \|__|\|__|     \|__|   \|_______|  \|_______|    ",
          r"                                                                 ",
          r"                                                                 ",
          r'Welcome to FAT32 reader, enter "help" to list available commands.', colors.END, sep='\n')


def print_help():
    print()
    print(colors.BOLD + "  cd <path>" + colors.END, "               - change directory to <path>")
    print(colors.BOLD + "  chpar <partition number>" + colors.END, "- change partition from 0 to 3")
    print(colors.BOLD + "  cp <file1> <file2>" + colors.END, "      - copy <file1> to <file2>")
    print(colors.BOLD + "  help" + colors.END, "                    - print this message")
    print(colors.BOLD + "  ls [-options] [<path>]" + colors.END, "  - print all directories and files within current "
                                                                 "directory or <path>")
    print("    -a                     - show hidden entries")
    print("    -l                     - show extra entry information")
    print(colors.BOLD + "  mkdir <directory>" + colors.END, "       - create <directory>")
    print(colors.BOLD + "  pwd" + colors.END, "                     - print working directory")
    print(colors.BOLD + "  quit|exit" + colors.END, "               - quit the application")
    print(colors.BOLD + "  rm [-options] <file>" + colors.END, "    - delete <file>")
    print("    -r                     - recursive (for deleting folders)")
    print()
