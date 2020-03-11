from utils import lba

MASK = 0x0FFFFFFF


class FileAllocationTable:
    def __init__(self, partition, lba_address):
        self.partition = partition
        self.first_sector = lba_address

    def next_cluster(self, cluster):
        last_position = self.partition.disk.image.tell()
        self.partition.disk.image.seek(lba(self.first_sector) + cluster * 4)
        next_cluster = int.from_bytes(self.partition.disk.image.read(4), byteorder="little")
        self.partition.disk.image.seek(last_position)
        return next_cluster & MASK

    def find_free_cluster(self, cluster=2):
        last_position = self.partition.disk.image.tell()
        self.partition.disk.image.seek(lba(self.first_sector) + (cluster + 1) * 4)
        current_cluster = int.from_bytes(self.partition.disk.image.read(4), byteorder="little") & MASK
        cluster_number = max(cluster + 1, 2)
        while current_cluster != 0x00000000:
            current_cluster = int.from_bytes(self.partition.disk.image.read(4), byteorder="little") & MASK
            cluster_number += 1
        self.partition.disk.image.seek(last_position)
        return cluster_number

    def write(self, cluster, next_cluster):
        last_position = self.partition.disk.image.tell()
        self.partition.disk.image.seek(lba(self.first_sector) + cluster * 4)
        self.partition.disk.image.write(next_cluster.to_bytes(4, byteorder="little"))
        self.partition.disk.image.seek(last_position)

    def print_chain(self, cluster):
        last_position = self.partition.disk.image.tell()
        self.partition.disk.image.seek(lba(self.first_sector) + cluster * 4)
        current_cluster = int.from_bytes(self.partition.disk.image.read(4), byteorder="little") & MASK
        print(current_cluster, end='')
        while current_cluster < 0x0FFFFFF8 or current_cluster == 0x00000000:
            current_cluster = self.next_cluster(current_cluster) & MASK
            print(" -> " + str(current_cluster), end='')
        print()
        self.partition.disk.image.seek(last_position)
