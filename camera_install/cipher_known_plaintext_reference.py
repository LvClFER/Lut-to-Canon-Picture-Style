"""Offline known-plaintext cipher reconstruction, with no Canon table constants.

Caller must supply authentic aligned plaintext/ciphertext and independently
validate the result. This neither discovers plaintext nor authorizes writing.
"""
from collections import deque


def recover_masked_tables(observations):
    """Combine proven partial bytes: (stream position, plain, cipher, mask).

    Only mask-selected plaintext bits are evidence. Every bit must connect
    all 1025 nodes; disconnected components must never be guessed. Keys are
    equivalent up to a common XOR byte, fixed here by setting node zero to0.
    No source parsing, implicit offsets or native resource discovery occurs.
    """
    if type(observations) is not tuple or not 1 <= len(observations) <= 262656:
        raise ValueError('Require bounded immutable masked evidence')
    graph = [[] for _ in range(1025)]
    for row in observations:
        if type(row) is not tuple or len(row) != 4:
            raise ValueError('Require position/plaintext/ciphertext/mask tuples')
        position, plain, cipher, mask = row
        if (type(position) is not int or not 0 <= position <= 0xffffffff
                or any(type(x) is not int or not 0 <= x <= 255
                       for x in (plain, cipher, mask)) or mask == 0):
            raise ValueError('Invalid masked cipher evidence')
        left, right = position % 512, 512 + position % 513
        value = plain ^ cipher ^ 0x37
        graph[left].append((right, value, mask))
        graph[right].append((left, value, mask))
    recovered = [0] * 1025
    incomplete = False
    for bit in range(8):
        flag = 1 << bit
        values = [None] * 1025
        components = 0
        for root in range(1025):
            if values[root] is not None:
                continue
            components += 1
            values[root] = 0
            pending = deque([root])
            while pending:
                node = pending.popleft()
                for other, edge, mask in graph[node]:
                    if not mask & flag:
                        continue
                    candidate = values[node] ^ (edge & flag)
                    if values[other] is None:
                        values[other] = candidate
                        pending.append(other)
                    elif values[other] != candidate:
                        raise ValueError('Known plaintext constraints are inconsistent')
        incomplete |= components != 1
        for node, value in enumerate(values):
            recovered[node] |= value
    if incomplete:
        raise ValueError('Evidence does not connect every cipher table position for every bit')
    return bytes(recovered[:512]), bytes(recovered[512:])


def recover_sparse_tables(observations):
    """Recover from explicitly known bytes across multiple blocks/seeds.

    Each immutable triple is (absolute stream position, plaintext byte,
    ciphertext byte). Positions are seed+offset, NOT file offsets. No missing
    plaintext is inferred. Reject incomplete coverage rather than filling keys.
    """
    if type(observations) is not tuple or not 1 <= len(observations) <= 262656:
        raise ValueError('Require bounded immutable sparse evidence')
    graph = [[] for _ in range(1025)]
    for observation in observations:
        if type(observation) is not tuple or len(observation) != 3:
            raise ValueError('Require position/plaintext/ciphertext triples')
        position, plain, cipher = observation
        if (type(position) is not int or not 0 <= position <= 0xffffffff
                or type(plain) is not int or not 0 <= plain <= 255
                or type(cipher) is not int or not 0 <= cipher <= 255):
            raise ValueError('Invalid sparse cipher evidence')
        left, right = position % 512, 512 + position % 513
        value = plain ^ cipher ^ 0x37
        graph[left].append((right, value))
        graph[right].append((left, value))
    values = [None] * 1025
    values[0] = 0
    pending = deque([0])
    while pending:
        node = pending.popleft()
        for other, edge in graph[node]:
            candidate = values[node] ^ edge
            if values[other] is None:
                values[other] = candidate
                pending.append(other)
            elif values[other] != candidate:
                raise ValueError('Known plaintext constraints are inconsistent')
    if any(value is None for value in values):
        raise ValueError('Evidence does not connect every cipher table position')
    return bytes(values[:512]), bytes(values[512:])


def recover_equivalent_tables(plaintext: bytes, ciphertext: bytes, *, seed: int):
    """Solve XOR constraints; reject incomplete or inconsistent evidence.

    Individual tables are ambiguous by one common XOR byte. Fixing the first
    byte to zero yields an equivalent stream, not Canon's original tables.
    """
    if type(plaintext) is not bytes or type(ciphertext) is not bytes:
        raise TypeError('Evidence must be immutable bytes')
    if len(plaintext) != len(ciphertext) or not 1024 <= len(plaintext) <= 262656:
        raise ValueError('Aligned evidence must contain 1024..262656 bytes')
    if type(seed) is not int or not 0 <= seed <= 0xffffffff - len(plaintext):
        raise ValueError('Seed must remain within the observed non-overflowing range')
    return recover_sparse_tables(tuple((seed+i, plain, cipher)
        for i, (plain, cipher) in enumerate(zip(plaintext, ciphertext))))
