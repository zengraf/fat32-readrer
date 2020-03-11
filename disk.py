import colors
from mbr import MasterBootRecord


class Disk:
    def __init__(self, image):
        self.image = image
        self.master_boot_record = MasterBootRecord(self)
        self.partitions = self.master_boot_record.partition_entries
        self.current_partition = self.partitions[0]

    def chpar(self, number):
        if number in range(4) and self.partitions[number].fat32:
            self.current_partition = self.partitions[number]
        else:
            print(colors.WARNING + "Partition", number, "is not FAT32" + colors.END)

    def pwd(self):
        self.current_partition.pwd()

    def ls(self, path='', include_hidden=False, long_list=False):
        self.current_partition.ls(path, include_hidden, long_list)

    def cd(self, path=''):
        self.current_partition.cd(path)

    def cp(self, origin, destination):
        self.current_partition.cp(origin, destination)

    def mkdir(self, directory):
        self.current_partition.mkdir(directory)

    def rm(self, path, recursive=False):
        self.current_partition.rm(path, recursive)
