# µPing (MicroPing) for MicroPython
# copyright (c) 2018 Shawwwn <shawwwn1@gmail.com>
# License: MIT

# Internet Checksum Algorithm
# Author: Olav Morken
# https://github.com/olavmrk/python-ping/blob/master/ping.py
# @data: bytes


def checksum(data):
    if len(data) & 0x1:  # Odd number of bytes
        data += b'\0'
    cs = 0
    for pos in range(0, len(data), 2):
        b1 = data[pos]
        b2 = data[pos + 1]
        cs += (b1 << 8) + b2
    while cs >= 0x10000:
        cs = (cs & 0xffff) + (cs >> 16)
    cs = ~cs & 0xffff
    return cs


def getRandomString(size):
    import random
    import gc
    gc.collect()
    printableCharacters = 'abcdefghijklmnopqrstuvwxyz1234567890ABCBEFHIJKLMNOPQRSTUVWXYZ'
    rs = ""
    for x in range(size):
        rs += random.choice(printableCharacters)
    return (rs)
    # return ''.join(random.choice(printableCharacters) for x in range(size))


def ping(host, size=16, timeout=5000, quiet=True):
    import utime
    import uctypes
    import usocket
    import ustruct
    import random
    import gc

    gc.collect()
    utime.sleep_ms(100)
    gc.collect()
    utime.sleep_ms(300)

    # Under 26 bytes, the echo responses may be a different size
    # from the echo request so best to do all two way
    # measurements based on at least 26 byte payloads.

    # 16 bytes seem to be the minimum for relable timings from experimenting
    assert size >= 16, "pkt size too small, must be > 16"

    assert size <= 1480, "pkt size too large, must be less then 1480"

    # prepare packet

    # Use a randomized string so that
    # network data compression does not impact ping times
    pkt = getRandomString(size).encode()
    # pkt = b'Q'*size

    # Build the packet header
    # See http://www.networksorcery.com/enp/protocol/icmp/msg8.htm for details
    pkt_desc = {
        "type": uctypes.UINT8 | 0,
        "code": uctypes.UINT8 | 1,
        "checksum": uctypes.UINT16 | 2,
        "id": uctypes.UINT16 | 4,
        "seq": uctypes.INT16 | 6,
        "timestamp": uctypes.UINT64 | 8,
    }  # packet header descriptor
    h = uctypes.struct(uctypes.addressof(pkt), pkt_desc, uctypes.BIG_ENDIAN)
    h.type = 8  # ICMP_ECHO_REQUEST
    h.code = 0
    h.checksum = 0
    h.id = random.randint(0, 65535)
    h.seq = 1

    # init socket
    sock = usocket.socket(usocket.AF_INET, usocket.SOCK_RAW, 1)
    sock.setblocking(0)
    sock.settimeout(timeout/1000)
    try:
        addr = usocket.getaddrinfo(host, 1)[0][-1][0]  # ip address
        # print("addr:", host, addr)
    except:
        print("addr fail:", host)
        return None
    sock.connect((addr, 1))
    t_elapsed = -1
    finish = False
    size_on_wire = 0

    # send packet
    h.checksum = 0
    h.seq = 1
    h.timestamp = utime.ticks_us()
    h.checksum = checksum(pkt)
    if sock.send(pkt) == size:
        # Successful packet send, Wait for ping to respond
        while True:
            try:
                resp = sock.recv(60)
            except Exception as err:
                not quiet and print("uping recv error", err)
                break
            resp_mv = memoryview(resp)
            h2 = uctypes.struct(uctypes.addressof(
                resp_mv[20:]), pkt_desc, uctypes.BIG_ENDIAN)
            size_on_wire = len(resp)
            # TODO: validate checksum (optional)
            if h2.type == 0 and h2.id == h.id:  # 0: ICMP_ECHO_REPLY
                t_elapsed = (utime.ticks_us()-h2.timestamp) / 1000
                ttl = ustruct.unpack('!B', resp_mv[8:9])[0]  # time-to-live
                not quiet and print("%u bytes from %s: ttl=%u, time=%f ms" %
                                    (len(resp), addr, ttl, t_elapsed))
                break

    # close
    sock.close()
    if t_elapsed == -1:
        # Timed out
        return None
    else:
        # Note: From wireshark actual size of datagram on wire is 14 bytes larger than recv length (Ethernet Frame header)
        return t_elapsed, ttl, (size_on_wire + 14)
