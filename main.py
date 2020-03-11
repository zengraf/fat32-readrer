import colors
from disk import Disk
from utils import print_mtod, split_paths, print_help


def console(image):
    while True:
        print(colors.BOLD + str(image.current_partition.number) + ":", end='')
        image.pwd()
        print(colors.END, end='')
        command = input(" >>> ").split(' ', 1)
        if command[0] == "ls":
            include_hidden = False
            long_list = False
            if len(command) > 1 and command[1][0] == '-':
                if 'a' in command[1][:4]:
                    include_hidden = True
                if 'l' in command[1][:4]:
                    long_list = True
                command = list([command[0], command[1][3:].strip()])
            path = command[1] if len(command) > 1 else ''
            image.ls(path, include_hidden, long_list)
        elif command[0] == "cd":
            image.cd(command[1])
        elif command[0] == "pwd":
            image.pwd()
            print()
        elif command[0] == "chpar":
            image.chpar(int(command[1]))
        elif command[0] == "cp":
            origin, destination = split_paths(command[1])
            image.cp(origin, destination)
        elif command[0] == "mkdir":
            image.mkdir(command[1])
        elif command[0] == "help":
            print_help()
        elif command[0] == "rm":
            recursive = False
            if len(command) > 1 and command[1][0] == '-':
                if 'r' in command[1][:3]:
                    recursive = True
                command = list([command[0], command[1][2:].strip()])
            image.rm(command[1], recursive)
        elif command[0] == "quit" or command[0] == "q" or command[0] == "exit":
            return
        else:
            print(colors.WARNING + "Unknown command:", command[0] + colors.END)


filename = input("Enter the name of disk image: ")
print()
f = open(filename, "r+b")
disk = Disk(f)
print_mtod()
console(disk)
