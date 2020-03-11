import datetime

import colors
from directory import Directory
from entry import Attrib, Entry
from fat import FileAllocationTable, MASK
from path import Path
from utils import lba, split_directory_file, short_filename


class Partition:
    def __init__(self, disk, number):
        self.number = number
        self.disk = disk
        last_position = self.disk.image.tell()
        self.disk.image.seek(0x1BE + self.number * 16 * 8)
        self.boot_flag = int.from_bytes(self.disk.image.read(1), byteorder="little")
        self.CHS_begin = int.from_bytes(self.disk.image.read(3), byteorder="little")
        self.partition_type = int.from_bytes(self.disk.image.read(1), byteorder="little")
        self.CHS_end = int.from_bytes(self.disk.image.read(3), byteorder="little")
        self.first_sector = int.from_bytes(self.disk.image.read(4), byteorder="little")
        self.sectors_number = int.from_bytes(self.disk.image.read(4), byteorder="little")

        self.fat32 = self.partition_type == 0x0B or self.partition_type == 0x0C

        if self.fat32:
            self.disk.image.seek(lba(self.first_sector) + 0x0B)
            self.bytes_per_sector = int.from_bytes(self.disk.image.read(2), byteorder="little")
            self.sectors_per_cluster = int.from_bytes(self.disk.image.read(1), byteorder="little")
            self.reserved_sectors = int.from_bytes(self.disk.image.read(2), byteorder="little")
            self.number_of_FATs = int.from_bytes(self.disk.image.read(1), byteorder="little")
            self.disk.image.seek(lba(self.first_sector) + 0x24)
            self.sectors_per_FAT = int.from_bytes(self.disk.image.read(4), byteorder="little")
            self.disk.image.seek(lba(self.first_sector) + 0x2C)
            self.root_cluster = int.from_bytes(self.disk.image.read(4), byteorder="little")

            self.disk.image.seek(lba(self.first_sector) + 0x1FE)
            print("Partition", number, "volume signature ................................. ", end='')
            if int.from_bytes(self.disk.image.read(2), byteorder="big") == 0x55AA:
                print(colors.OK + "OK" + colors.END)
            else:
                print(colors.FAIL + "FAIL" + colors.END)

            self.fat = list()
            for i in range(self.number_of_FATs):
                self.fat.append(
                    FileAllocationTable(self, self.first_sector + self.reserved_sectors + i * self.sectors_per_FAT))

            self.first_cluster = self.first_sector + self.reserved_sectors + self.number_of_FATs * self.sectors_per_FAT

            self.current_directory = Directory(self, self.root_cluster)
            self.current_path = Path()

        self.disk.image.seek(last_position)

    def get_sector(self, cluster):
        return self.first_cluster + max(cluster - 2, 0) * self.sectors_per_cluster

    def get_directory(self, path):
        if path == '':
            return self.current_directory

        if path[0] == '/':
            directory = Directory(self, self.root_cluster)
            path = path[1:]
        else:
            directory = self.current_directory

        for p in path.replace(r'\ ', ' ').split('/'):
            if p == '':
                continue
            result = [entry for entry in directory.entries if entry.attrib.subdirectory and entry.name() == p]
            if len(result) == 0:
                print(colors.WARNING + '"' + path + '" is not a directory' + colors.END)
                return
            directory = Directory(self, result[0].cluster)

        return directory

    def create_directory(self, directory, name, attrib=0x10):
        if name in [e.name() for e in directory.entries]:
            print(name, " already exists in directory")
            return None

        cluster = self.next_free_cluster()

        filename, extension = short_filename(name, directory)
        if name == filename.strip() + ('.' + extension.strip()) if len(extension.strip()) != 0 else '':
            name = ''

        today = datetime.datetime.today()
        milliseconds = today.microsecond // 10000 + (today.second % 2) * 100

        entry = Entry(filename, extension, Attrib(attrib), 0x00, milliseconds, today.time(),
                      today.date(), today.date(), today.time(), today.date(), cluster, 0, name)
        directory.write(entry)
        self.current_directory.read_from_disk()

        self.write_to_fat(cluster, 0x0FFFFFFF)

        new_directory = Directory(self, cluster)
        self_entry = Entry(".       ", "   ", Attrib(0x10), 0x00, milliseconds, today.time(),
                           today.date(), today.date(), today.time(), today.date(), cluster, 0, '')
        new_directory.write(self_entry)
        new_directory.read_from_disk()

        up_entry = Entry("..      ", "   ", Attrib(0x10), 0x00, milliseconds, today.time(), today.date(),
                         today.date(), today.time(), today.date(), directory.first_cluster, 0, '')
        new_directory.write(up_entry)

    def delete_directory(self, directory, name):
        entry = [e for e in directory.entries if e.name() == name][0]
        current_directory = Directory(self, entry.cluster)

        self.delete_entry(directory, name)
        for e in current_directory.entries:
            if e.name() == "." or e.name() == "..":
                continue
            if e.attrib.subdirectory:
                self.delete_directory(current_directory, e.name())
            else:
                self.delete_entry(current_directory, e.name())

        directory.read_from_disk()

    def get_file(self, path):
        directory_path, name = split_directory_file(path)
        directory = self.get_directory(directory_path)
        if directory is None:
            return
        result = [entry for entry in directory.entries if
                  not entry.attrib.subdirectory and entry.name() == name]
        if len(result) == 0:
            return
        return result[0]

    def copy_file(self, origin_entry, directory, long_filename):
        last_position = self.disk.image.tell()

        cluster = self.next_free_cluster()

        filename, extension = short_filename(long_filename, directory)
        if long_filename == filename.strip() + ('.' + extension.strip()) if len(extension.strip()) != 0 else '':
            long_filename = ''
        destination_entry = Entry.from_entry(origin_entry, filename, extension, cluster, long_filename)
        directory.write(destination_entry)

        self.copy_cluster_chain(origin_entry.cluster, cluster)
        self.disk.image.seek(last_position)

    def delete_entry(self, directory, name):
        last_position = self.disk.image.tell()
        entry = [e for e in directory.entries if e.name() == name][0]
        self.disk.image.seek(lba(self.get_sector(directory.first_cluster)) + entry.first_line * 32)
        for i in range(entry.length):
            self.disk.image.write(b'\xE5')
            self.disk.image.seek(31, 1)

        self.delete_cluster_chain(entry.cluster)
        directory.read_from_disk()
        self.disk.image.seek(last_position)

    def next_cluster(self, cluster):
        cluster_values = list()
        for f in self.fat:
            cluster_values.append(f.next_cluster(cluster))

        if len(set(cluster_values)) != 1:
            print(colors.WARNING + "FAT entries are not the same" + colors.END)

        return cluster_values[0]

    def next_free_cluster(self, cluster=2):
        cluster_values = list()
        for f in self.fat:
            cluster_values.append(f.find_free_cluster(cluster))

        if len(set(cluster_values)) != 1:
            print(colors.WARNING + "FAT entries are not the same" + colors.END)

        return cluster_values[0]

    def write_to_fat(self, cluster, next_cluster):
        for f in self.fat:
            f.write(cluster, next_cluster)

    def read_cluster(self, cluster):
        last_position = self.disk.image.tell()
        self.disk.image.seek(lba(self.get_sector(cluster)))
        data = self.disk.image.read(self.bytes_per_sector * self.sectors_per_cluster)
        self.disk.image.seek(last_position)
        return data

    def write_cluster(self, cluster, data):
        last_position = self.disk.image.tell()
        self.disk.image.seek(lba(self.get_sector(cluster)))
        self.disk.image.write(data)
        self.disk.image.seek(last_position)

    def copy_cluster(self, origin_cluster, destination_cluster):
        self.write_cluster(destination_cluster, self.read_cluster(origin_cluster))

    def delete_cluster(self, cluster):
        next_cluster = self.next_cluster(cluster) & MASK
        self.write_to_fat(cluster, 0x00000000)
        return next_cluster

    def copy_cluster_chain(self, origin_cluster, destination_cluster):
        origin_current_cluster = origin_cluster & MASK
        destination_current_cluster = destination_cluster & MASK
        while origin_current_cluster < 0x0FFFFFF8:
            self.copy_cluster(origin_current_cluster, destination_current_cluster)
            origin_current_cluster = self.next_cluster(origin_current_cluster) & MASK
            next_cluster = self.next_free_cluster(destination_current_cluster) & MASK
            self.write_to_fat(destination_current_cluster,
                              next_cluster if origin_current_cluster < 0x0FFFFFF8 else 0x0FFFFFFF)
            destination_current_cluster = next_cluster

    def delete_cluster_chain(self, first_cluster):
        current_cluster = first_cluster
        while current_cluster < 0x0FFFFFF8:
            current_cluster = self.delete_cluster(current_cluster)

    def pwd(self):
        print(self.current_path.to_string(), end='')

    def ls(self, path='', include_hidden=False, long_list=False):
        directory = self.current_directory if path == '' else self.get_directory(path)
        if directory is None:
            return

        for entry in directory.entries:
            if include_hidden or not entry.attrib.hidden:
                if long_list:
                    print(int.from_bytes(entry.attrib.encode(), byteorder="little"), entry.create_date,
                          entry.create_time, entry.modification_date, entry.modification_time, entry.name(),
                          entry.cluster, entry.size)
                else:
                    print(entry.name(), end='   ')
        if not long_list:
            print()

    def cd(self, path):
        directory = self.get_directory(path)
        if directory is None:
            return
        self.current_directory = directory
        self.current_path.go_into(path)

    def cp(self, origin, destination):
        origin_file = self.get_file(origin)
        if origin_file is None:
            print(colors.WARNING + 'File "' + origin, '" does not exist' + colors.END)
            return
        if self.get_file(destination) is not None:
            print(colors.WARNING + '"' + destination, '" already exists' + colors.END)
            return
        destination, name = split_directory_file(destination)
        destination_directory = self.get_directory(destination)
        if destination_directory is None:
            return
        if any(char in name for char in ['\\', ':', '*', '?', '"', '<', '>', '|']):
            print(colors.WARNING + "Destination filename contains prohibited symbols (\\ : * ? \" < > |)" + colors.END)
            return

        self.copy_file(origin_file, destination_directory, name)
        self.current_directory.read_from_disk()

    def mkdir(self, path):
        working_directory_path, name = split_directory_file(path)
        working_directory = self.get_directory(working_directory_path)
        if working_directory is None:
            print(colors.WARNING + 'Directory "' + working_directory_path + '" does not exist' + colors.END)
            return
        if self.get_file(path) is not None:
            print(colors.WARNING + '"' + path + '" already exists' + colors.END)
            return
        if any(char in name for char in ['\\', ':', '*', '?', '"', '<', '>', '|']):
            print(colors.WARNING + "Destination filename contains prohibited symbols (\\ : * ? \" < > |)" + colors.END)
            return

        self.create_directory(working_directory, name)

    def rm(self, path, recursive=False):
        directory_path, name = split_directory_file(path)
        directory = self.get_directory(directory_path)
        if directory is None:
            print(colors.WARNING + 'Directory "' + directory_path + '" does not exist' + colors.END)
            return
        if self.get_directory(path) is not None and not recursive:
            print(colors.WARNING + '"' + path + '" is a directory' + colors.END)
            return
        file = self.get_file(path)
        if (recursive and self.get_directory(path) is None and file is None) or (not recursive and file is None):
            print(colors.WARNING + '"' + path + '" does not exist' + colors.END)
            return
        if recursive and self.get_directory(path):
            self.delete_directory(directory, name)
        else:
            self.delete_entry(directory, name)

    def print(self):
        print("\n  Partition", self.number)
        print("  Boot flag:", format(self.boot_flag, '#04x'))
        print("  CHS begin:", format(self.CHS_begin, '#08x'))
        print("  Partition type:", format(self.partition_type, '#04x'))
        print("  CHS end:", format(self.CHS_end, '#08x'))
        print("  First sector:", format(self.first_sector, '#010x'))
        print("  Sectors number:", self.sectors_number)
        if self.fat32:
            print("  Bytes per sector:", self.bytes_per_sector)
            print("  Sectors per cluster:", self.sectors_per_cluster)
            print("  Number of reserved sectors:", self.reserved_sectors)
            print("  Number of FATs:", self.number_of_FATs)
            print("  Sectors Per FAT:", self.sectors_per_FAT)
            print("  Root directory first sector:", format(self.root_cluster, '#06x'))
