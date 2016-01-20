import vesicle


class BPB(vesicle.Vesicle):
    magic = vesicle.fixed(0, 0xEB, 0x3C, 0x90)  # TODO: support different middle bytes
    oem_id = vesicle.ascii(3, len=8, padding=0x20)
    sector_size = vesicle.uint16l(11)  # bytes per sector
    cluster_size = vesicle.uint8(13)  # sectors per cluster
    reserved_sectors = vesicle.uint16l(14)  # reserved sectors, including boot record
    fat_count = vesicle.uint8(16)
    directory_entries = vesicle.uint16l(17)
    total_sectors = vesicle.uint16l(19)
    media_descriptor = vesicle.uint8(21)  # just set to 0xF8
    sectors_per_fat = vesicle.uint16l(22)
    sectors_per_track = vesicle.uint16l(24)
    media_sides = vesicle.uint16l(26)
    hidden_sectors = vesicle.uint32l(28)
    extended_sector_count = vesicle.uint32l(32)
    expected_length = 36
    total_size = sector_size * total_sectors


class EBPB(vesicle.Vesicle):
    bpb = BPB(0)
    drive_number = vesicle.uint8(36)  # just set to 0x80
    reserved_flags = vesicle.uint8(37)
    signature = vesicle.uint8(38)  # just set to 0x29
    serial_number = vesicle.uint32l(39)  # doesn't really matter
    volume_label = vesicle.ascii(43, len=11, padding=0x20)
    system_identifier = vesicle.ascii(54, len=8, padding=0x20)
    boot_code = vesicle.byte_array(62, len=448)
    partition_signature = vesicle.fixed(510, 0x55, 0xAA)
    expected_length = 512


with open("test", "rb") as f:
    data = f.read(EBPB.expected_length)
    print(EBPB.parse(data))
