"""Pure Python replay of stop paths in success and current cores; no ROS IO."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace as S

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'evaluation3_reference_wait/candidate/follower_diagnostics'
CURRENT=ROOT/'evaluation3_ekf_wait/candidate/follower_diagnostics'
sys.path.insert(0,str(CURRENT))


def load(folder,name,label):
    spec=importlib.util.spec_from_file_location(label+'_'+name,folder/(name+'.py'))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replay(folder,label):
    continuous=load(folder,'continuous_local_core',label)
    pause_module=load(folder,'continuous_near_return_pause',label)
    local=load(folder,'local_stop_turn_go',label)
    tracker=load(folder,'directed_path_tracker',label)
    preview=load(folder,'follower_pursuit_preview',label)
    motor=dict(armed=True,feedback_fresh=True,measured_rpm=[0,0],zero_feedback_samples=5)
    results={}
    for key in ('raw','filtered','imu'):
        core=local.LocalCore(pose_source='filtered')
        for k in ('raw','filtered','imu','leader'):
            core.inputs[k]=(9_000_000_000 if k==key else 10_000_000_000,
                            9. if k==key else 10.,(0.,0.,0.,0.,0.))
        try:core.scene(10_000_000_000,10.)
        except ValueError as e:results[key+'_stale']=str(e)
    core=local.LocalCore(pose_source='filtered')
    for k in ('raw','filtered','imu','leader'):core.inputs[k]=(10_000_000_000,10.,(0.,0.,0.,0.,0.))
    core.freeze((0.,0.,0.),(0.,0.,0.));core.scan=(9_000_000_000,9.,np.array([[5.,5.]]))
    try:core.scene(10_000_000_000,10.)
    except ValueError as e:results['scan_stale']=str(e)
    for speed,yaw,name in ((-.02,0.,'leader_reverse'),(0.,.11,'leader_rotation')):
        core.inputs['leader']=(10_000_000_000,10.,(2.,0.,0.,speed,yaw))
        try:core.scene(10_000_000_000,10.)
        except ValueError as e:results[name+'_local_scene']=str(e)
    for speed,yaw,name in ((-.02,0.,'leader_reverse'),(0.,.06,'leader_rotation')):
        nav=preview.PreviewCore();stamp=S(sec=10,nanosec=0)
        nav.inputs={'leader':(stamp,10.,(2.,0.,0.,speed,yaw)),
                    'follower':(stamp,10.,(0.,0.,0.,0.,0.)),
                    'path':(stamp,10.,((0.,0.),(2.,0.)))}
        nav.leader_moving=True
        results[name+'_speed_gate']=nav.speed_gate(10_000_000_000,10.)[2]
    core=continuous.ContinuousCore(pose_source='filtered')
    pose=S(x=0.,y=0.,yaw=0.)
    core.scene=lambda *_:dict(pose=pose,points=np.array([[10.,10.]]),uncertainty=.01,
        source=10_000_000_000,scan_stamp=10_000_000_000,source_stamps={})
    core.last_pose=(0.,0.,0.)
    pose.x=.11
    results['after_long_gap_pose_delta_11cm']=core.command(10_000_000_000,10.,motor,(.02,0.))['reason']
    pose.x=4.51
    results['workspace_forward_4_51m']=core.command(10_000_000_000,10.,motor,(.02,0.))['reason']
    pose.x=0.;pose.y=1.26
    results['workspace_side_1_26m']=core.command(10_000_000_000,10.,motor,(.02,0.))['reason']
    pause=pause_module.ContinuousNearReturnPause()
    row=dict(reason='STOP_SWEPT_CLEARANCE',v=0.,w=0.,motion='STOP',clearance_m=.2,
             swept_clearance_m=.04,scan_stamp_ns=10_000_000_000)
    results['swept_clearance_without_active_pause']=pause.apply(row,10.,motor)['reason']
    row.update(reason='STOP_FOOTPRINT_CLEARANCE',clearance_m=.04)
    results['footprint_starts_pause']=pause.apply(row,10.,motor)['reason']
    results['footprint_after_two_seconds']=pause.apply(row,12.,motor)['reason']
    path=tracker.DirectedPathTracker();path.observe_position((0.,0.,0.))
    try:path.observe_position((.21,0.,0.))
    except ValueError as e:results['map_position_step_21cm']=str(e)
    path=tracker.DirectedPathTracker();path.select(((0.,0.),(1.,0.)),(0.,0.,0.),.35)
    try:path.select(((.1,0.),(1.,0.)),(0.,0.,0.),.35)
    except ValueError as e:results['path_prefix_replaced']=str(e)
    return results


def main():
    dependencies=('continuous_local_core','continuous_near_return_pause','local_stop_turn_go',
                  'directed_path_tracker','follower_pursuit_preview','map_rejoin_guidance',
                  'reference_wait','evaluation3_clearance_policy','continuous_avoidance_candidate')
    hashes={name:hashlib.sha256((BASE/(name+'.py')).read_bytes()).hexdigest()==
                 hashlib.sha256((CURRENT/(name+'.py')).read_bytes()).hexdigest() for name in dependencies}
    assert all(hashes.values()),hashes
    original=replay(BASE,'success');current=replay(CURRENT,'current')
    assert original==current,(original,current)
    expected={'raw_stale':'RAW_STALE','filtered_stale':'FILTERED_STALE','imu_stale':'IMU_STALE',
        'scan_stale':'SCAN_STALE','leader_reverse_local_scene':'LEADER_UNEXPECTED_MOTION',
        'leader_rotation_local_scene':'LEADER_UNEXPECTED_MOTION','leader_reverse_speed_gate':'STOP_LEADER_REVERSE',
        'leader_rotation_speed_gate':'STOP_LEADER_ROTATING','after_long_gap_pose_delta_11cm':'STOP_FILTERED_ODOM_JUMP',
        'workspace_forward_4_51m':'STOP_APF_WORKSPACE_BOUND','workspace_side_1_26m':'STOP_APF_WORKSPACE_BOUND',
        'swept_clearance_without_active_pause':'STOP_SWEPT_CLEARANCE','footprint_starts_pause':'NEAR_RETURN_PAUSE',
        'footprint_after_two_seconds':'STOP_NEAR_RETURN_WAIT_TIMEOUT','map_position_step_21cm':'PATH_FOLLOWER_MAP_JUMP',
        'path_prefix_replaced':'PATH_SESSION_CHANGED_RESTART'}
    assert current==expected,(current,expected)
    output=dict(mode='OFFLINE_PURE_FUNCTIONS_NO_ROS_OR_SERIAL',identical_dependencies=hashes,
        compared_scenarios=len(current),success=current,current=current,all_equal=True,
        limitation='Operator catch/abort paths also reviewed statically; not full physical ROS scheduling replay')
    dest=Path(__file__).with_name('behavior_comparison.json')
    dest.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print('Compared',len(current),'scenarios in both profiles; all matched expected outcomes.')
    print('REPORT='+str(dest))


if __name__=='__main__':main()
