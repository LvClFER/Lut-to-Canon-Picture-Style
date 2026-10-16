"""Offline reference for the observed descriptor-node copy length guard.

Not a descriptor parser or camera compatibility prediction. The known-revision
46de0 guard refuses an oversized request unless storage type is 2 (which can
truncate). Passing this guard does not prove later copying succeeds.
"""


def length_guard_rejects(stored_length, requested_length, storage_type):
    for value in (stored_length, requested_length, storage_type):
        if type(value) is not int or not 0 <= value <= 0xffffffff:
            raise ValueError('Expected unsigned 32-bit native fields')
    return requested_length > stored_length and storage_type != 2


def verify_observation(observation):
    rejected = length_guard_rejects(
        observation['storedLength'], observation['requestedLength'],
        observation['storageType'])
    if rejected and observation['succeeded'] is not False:
        raise ValueError('Native success contradicts the observed length guard')
    return {'lengthGuardRejects': rejected,
            'shortfall': max(0, observation['requestedLength'] - observation['storedLength'])}
