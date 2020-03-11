import math
import datetime

from fat import MASK


class Attrib:
    READ_ONLY = 0x01
    HIDDEN = 0x02
    SYSTEM = 0x04
    VOLUME_LABEL = 0x08
    SUBDIRECTORY = 0x10
    ARCHIVE = 0x20
    DEVICE = 0x40
    UNUSED = 0x80

    def __init__(self, attrib):
        self.read_only = attrib & Attrib.READ_ONLY > 0
        self.hidden = attrib & Attrib.HIDDEN > 0
        self.system = attrib & Attrib.SYSTEM > 0
        self.volume_label = attrib & Attrib.VOLUME_LABEL > 0
        self.subdirectory = attrib & Attrib.SUBDIRECTORY > 0
        self.archive = attrib & Attrib.ARCHIVE > 0
        self.device = attrib & Attrib.DEVICE > 0
        self.unused = attrib & Attrib.UNUSED > 0

    def encode(self):
        attrib = 0
        if self.read_only:
            attrib |= Attrib.READ_ONLY
        if self.hidden:
            attrib |= Attrib.HIDDEN
        if self.system:
            attrib |= Attrib.SYSTEM
        if self.volume_label:
            attrib |= Attrib.VOLUME_LABEL
        if self.subdirectory:
            attrib |= Attrib.SUBDIRECTORY
        if self.archive:
            attrib |= Attrib.ARCHIVE
        if self.device:
            attrib |= Attrib.DEVICE
        if self.unused:
            attrib |= Attrib.UNUSED
        return attrib.to_bytes(1, byteorder="little")


class Entry:
    YEAR_MASK = 0xFE00
    MONTH_MASK = 0x1E0
    DAY_MASK = 0x1F
    HOUR_MASK = 0xF800
    MINUTE_MASK = 0x7E0
    SECOND_MASK = 0x1F

    def __init__(self, filename, extension, attrib, case_information, create_time_ms,
                 create_time, create_date, last_access_date, modification_time,
                 modification_date, cluster, size, long_filename, first_line=0, length=0):
        self.first_line = first_line
        self.length = length
        self.filename = filename
        self.extension = extension
        self.attrib = attrib
        self.case_information = case_information
        self.create_time_ms = create_time_ms
        self.create_time = create_time
        self.create_date = create_date
        self.last_access_date = last_access_date
        self.modification_time = modification_time
        self.modification_date = modification_date
        self.cluster = cluster
        self.size = size
        self.long_filename = long_filename

    @classmethod
    def from_binary(cls, data, first_line=0):
        if data[-1][0] == 0x05:
            data[-1][0] = 0xE5

        cluster_high = int.from_bytes(data[-1][20:22], byteorder="little")
        cluster_low = int.from_bytes(data[-1][26:28], byteorder="little")
        long_filename = b''.join([(d[1:11] + d[14:26] + d[28:32]) for d in reversed(data[:-1])]).split(b'\xff\xff', 1)[
                            0].decode('utf-16')[:-1]

        return cls(data[-1][0:8].decode(), data[-1][8:11].decode(), Attrib(data[-1][11]),
                   data[-1][12], data[-1][13], Entry.decode_time(data[-1][14:16]), Entry.decode_date(data[-1][16:18]),
                   Entry.decode_date(data[-1][18:20]), Entry.decode_time(data[-1][22:24]),
                   Entry.decode_date(data[-1][24:26]), ((cluster_high << 16) + cluster_low) & MASK,
                   int.from_bytes(data[-1][28:32], byteorder="little"), long_filename, first_line, len(data))

    @classmethod
    def from_entry(cls, entry, filename, extension, cluster, long_filename, first_line=0, length=0):
        return cls(filename, extension, entry.attrib, entry.case_information, entry.create_time_ms,
                   entry.create_time, entry.create_date, entry.last_access_date, entry.modification_time,
                   entry.modification_date, cluster, entry.size, long_filename, first_line, length)

    @classmethod
    def decode_date(cls, date):
        date = int.from_bytes(date, byteorder="little")
        year = ((date & cls.YEAR_MASK) >> 9) + 1980
        month = (date & cls.MONTH_MASK) >> 5
        day = date & cls.DAY_MASK
        return datetime.date(year, month, day)

    @classmethod
    def decode_time(cls, time):
        time = int.from_bytes(time, byteorder="little")
        hour = (time & cls.HOUR_MASK) >> 11
        minute = (time & cls.MINUTE_MASK) >> 5
        second = (time & cls.SECOND_MASK) << 1
        return datetime.time(hour, minute, second, 0)

    @classmethod
    def encode_date(cls, date):
        return (((date.year - 1980) << 9) + (date.month << 5) + date.day).to_bytes(2, byteorder="little")

    @classmethod
    def encode_time(cls, time):
        return ((time.hour << 11) + (time.minute << 5) + (time.second >> 1)).to_bytes(2, byteorder="little")

    def name(self):
        filename = self.long_filename
        if len(filename) == 0:
            filename = self.filename.strip()
            if len(self.extension.strip()) != 0:
                filename += '.' + self.extension.strip()

        return filename

    def short_name_checksum(self):
        checksum = 0
        for char in self.filename + self.extension:
            checksum = (((checksum << 7) | (checksum >> 1)) + ord(char)) & 0xFF
        return checksum.to_bytes(1, byteorder="little")

    def encode(self):
        data = list()
        if ord(self.filename[0]) == 0xE5:
            buffer = b'\x05' + (self.filename[1:] + self.extension).encode('ascii')
        else:
            buffer = (self.filename + self.extension).encode('ascii')
        buffer += self.attrib.encode()
        buffer += self.case_information.to_bytes(1, byteorder="little")
        buffer += self.create_time_ms.to_bytes(1, byteorder="little")
        buffer += Entry.encode_time(self.create_time) + Entry.encode_date(self.create_date)
        buffer += Entry.encode_date(self.last_access_date)
        buffer += (self.cluster >> 16).to_bytes(2, byteorder="little")
        buffer += Entry.encode_time(self.modification_time) + Entry.encode_date(self.modification_date)
        buffer += (self.cluster & 0x0000FFFF).to_bytes(2, byteorder="little")
        buffer += self.size.to_bytes(4, byteorder="little")
        data.append(buffer)

        if len(self.long_filename) != 0:
            chunks = math.ceil((len(self.long_filename) + 1) / 13)
            long_filename = (self.long_filename.encode("utf-16") + b'\x00\x00').ljust(chunks * 26, b'\xff')
            long_filename = [long_filename[i:i + 26] for i in range(0, chunks * 26, 26)]
            for i in range(chunks):
                data.append((i + (0x41 if i == len(long_filename) - 1 else 1)).to_bytes(1, byteorder="little") +
                            long_filename[i][0:10] + b'\x0f\x00' + self.short_name_checksum() +
                            long_filename[i][10:22] + b'\x00\x00' + long_filename[i][22:26])

        return list(reversed(data))
