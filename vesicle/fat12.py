import vesicle, synthase, concrete_types


class BPB(vesicle.Vesicle):
    expected_length = 36

    def __init__(self, b):
        data = self.begin(b)
        data.fixed(0, 0xEB, 0x3C, 0x90)  # TODO: support different middle bytes
        self.oem_id = data.ascii(3, length=8, padding=0x20)
        self.sector_size = data.uint16l(11)  # bytes per sector
        self.cluster_size = data.uint8(13)  # sectors per cluster
        self.reserved_sectors = data.uint16l(14)  # reserved sectors, including boot record
        self.fat_count = data.uint8(16)
        self.directory_entries = data.uint16l(17)
        self.total_sectors = data.uint16l(19)
        self.media_descriptor = data.uint8(21)  # just set to 0xF8
        self.sectors_per_fat = data.uint16l(22)
        self.sectors_per_track = data.uint16l(24)
        self.media_sides = data.uint16l(26)
        self.hidden_sectors = data.uint32l(28)
        self.extended_sector_count = data.uint32l(32)
        self.total_size = self.sector_size * self.total_sectors


class EBPB(vesicle.Vesicle):
    expected_length = 512

    def __init__(self, b):
        data = self.begin(b)
        self.bpb = data.subparse(0, BPB)
        self.drive_number = data.uint8(36)  # just set to 0x80
        self.reserved_flags = data.uint8(37)
        self.signature = data.uint8(38)  # just set to 0x29
        self.serial_number = data.uint32l(39)  # doesn't really matter
        self.volume_label = data.ascii(43, length=11, padding=0x20)
        self.system_identifier = data.ascii(54, length=8, padding=0x20)
        self.boot_code = data.byte_array(62, length=448)
        self.partition_signature = data.fixed(510, 0x55, 0xAA)


with open("test", "rb") as f:
    synthase.compile(lambda x: EBPB(x).bpb.total_size, concrete_types.binary, rettype=concrete_types.u32)
    print(EBPB(f.read(512)))
