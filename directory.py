from entry import Entry
from fat import MASK
from utils import lba


class Directory:
    def __init__(self, partition, first_cluster):
        self.partition = partition
        self.first_cluster = first_cluster & MASK
        self.read_from_disk()

    def read_from_disk(self):
        last_position = self.partition.disk.image.tell()

        entry_block = list()
        self.entries = list()
        self.free_entries = list()
        entries_per_cluster = self.partition.sectors_per_cluster * self.partition.bytes_per_sector // 32
        first_free_entry_number = -1
        first_entry_number = -1
        current_cluster = self.first_cluster

        while current_cluster < 0x0FFFFFF8:
            self.partition.disk.image.seek(lba(self.partition.get_sector(current_cluster)))

            for entry_number in range(0, entries_per_cluster):
                entry = self.partition.disk.image.read(32)
                if entry[0] == 0x00:
                    if first_free_entry_number != -1:
                        self.free_entries.append(
                            (first_free_entry_number, (entries_per_cluster - first_free_entry_number), True))
                    else:
                        self.free_entries.append((entry_number, entries_per_cluster - entry_number, True))
                    first_free_entry_number = -1
                    break
                elif entry[0] == 0xE5:
                    if first_free_entry_number == -1:
                        first_free_entry_number = entry_number
                    continue
                else:
                    if first_entry_number == -1:
                        first_entry_number = entry_number
                    if first_free_entry_number != -1:
                        self.free_entries.append(
                            (first_free_entry_number, entry_number - first_free_entry_number, False))
                        first_free_entry_number = -1
                    entry_block.append(entry)
                    if entry[11] != 0x0F:
                        self.entries.append(Entry.from_binary(entry_block, first_entry_number))
                        first_entry_number = -1
                        entry_block = list()

            current_cluster = self.partition.next_cluster(current_cluster)

        self.partition.disk.image.seek(last_position)

    def write(self, entry):
        last_position = self.partition.disk.image.tell()
        entry = entry.encode()

        free_entry = self.free_entries[0]
        for e in self.free_entries:
            if e[1] > len(entry) or e[2]:
                free_entry = e

        current_directory_cluster = self.first_cluster
        while free_entry[0] > self.partition.bytes_per_sector * self.partition.sectors_per_cluster / 32:
            current_directory_cluster = self.partition.next_cluster(current_directory_cluster)
            free_entry[0] -= self.partition.bytes_per_sector * self.partition.sectors_per_cluster / 32

        self.partition.disk.image.seek(lba(self.partition.get_sector(current_directory_cluster)) + free_entry[0] * 32)
        if free_entry[2]:
            if len(entry) < free_entry[1]:
                self.partition.disk.image.write(b''.join(entry))
            else:
                self.partition.disk.image.write(b''.join(entry[:free_entry[1]]))
                self.partition.write_to_fat(current_directory_cluster,
                                            self.partition.next_free_cluster(current_directory_cluster))
                if len(entry[free_entry[1]:]) != 0:
                    self.partition.disk.image.write(b''.join(entry[free_entry[1]:]))
            self.partition.disk.image.write(b'\xe5')
        else:
            self.partition.disk.image.write(b''.join(entry))

        self.partition.disk.image.seek(last_position)
