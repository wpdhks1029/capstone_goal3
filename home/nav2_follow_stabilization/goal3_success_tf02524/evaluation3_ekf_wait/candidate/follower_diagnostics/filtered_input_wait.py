"""Filtered odom delay gates motion; a fresh raw/IMU/scan set can prove STOP only."""
from reference_wait import MAX_MOTION_SOURCE_AGE_S
from local_avoidance_limits import SOURCE_TIMEOUT_S

class FilteredUnavailable(ValueError):pass

def filtered_stamp(core,now,mono):
    row=core.inputs.get('filtered')
    if row is None:raise ValueError('FILTERED_MISSING')
    stamp,rx=row[:2]
    if type(stamp) is not int or stamp<=0:raise ValueError('FILTERED_TIMESTAMP_INVALID')
    if now<stamp or mono<rx:raise ValueError('FILTERED_FUTURE')
    if (now-stamp)/1e9>MAX_MOTION_SOURCE_AGE_S or mono-rx>MAX_MOTION_SOURCE_AGE_S:
        raise FilteredUnavailable('FILTERED_NOT_FRESH_FOR_MOTION')
    return stamp

def fresh_zero_sources(core,now,mono):
    # Does not compute a pose, heading, collision scene or motion command.
    # Stale filtered data is never re-stamped or added to a movement source set.
    stamps={}
    for key in ('raw','imu'):
        row=core.inputs.get(key)
        if row is None:raise ValueError(key.upper()+'_MISSING')
        stamp,rx=row[:2]
        if type(stamp) is not int or stamp<=0 or not 0<=(now-stamp)/1e9<=SOURCE_TIMEOUT_S or not 0<=mono-rx<=SOURCE_TIMEOUT_S:
            raise ValueError(key.upper()+'_STALE')
        stamps[key]=stamp
    if core.scan is None:raise ValueError('SCAN_MISSING_OR_INVALID')
    stamp,rx=core.scan[:2]
    if type(stamp) is not int or stamp<=0 or not 0<=(now-stamp)/1e9<=SOURCE_TIMEOUT_S or not 0<=mono-rx<=SOURCE_TIMEOUT_S:
        raise ValueError('SCAN_STALE')
    stamps['scan']=stamp
    return dict(source=min(stamps.values()),scan_stamp=stamp,source_stamps=stamps)
