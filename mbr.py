import colors
from partition import Partition


class MasterBootRecord:
    def __init__(self, disk):
        self.disk = disk
        last_position = self.disk.image.tell()
        self.disk.image.seek(0x1B8)
        self.disk_signature = int.from_bytes(self.disk.image.read(4), byteorder="big")
        self.copy_protected = int.from_bytes(self.disk.image.read(2), byteorder="big") == 0x5A5A
        self.partition_entries = []
        for i in range(4):
            self.partition_entries.append(Partition(self.disk, i))
        self.disk.image.seek(0x1FE)
        print("Boot signature ............................................... ", end='')
        if int.from_bytes(self.disk.image.read(2), byteorder="big") == 0x55AA:
            print(colors.OK + "OK" + colors.END)
        else:
            print(colors.FAIL + "FAIL" + colors.END)

        self.disk.image.seek(last_position)

    def print(self):
        print("\nDisk signature:", format(self.disk_signature, '#06x'))
        print("Copy protected:", self.copy_protected)
        print("Partition entries:")
        for p in self.partition_entries:
            p.print()
