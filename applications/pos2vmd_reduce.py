#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
from PyQt5.QtGui import QQuaternion, QVector4D, QVector3D, QMatrix4x4
import logging
import math

logger = logging.getLogger("__main__").getChild(__name__)

def reduce_frames(bone_frame_dic, is_groove, threshold_pos, threshold_rot):
    reduce_bone_frame_dic = {}

    for key in bone_frame_dic.keys():
        # logger.debug("key %s", key)
        if len(bone_frame_dic[key]) > 0 and ((is_groove == False and key != "グルーブ") or is_groove):
            reduce_bone_frame_dic[key] = reduce_bone_frame(bone_frame_dic[key], 0, len(bone_frame_dic[key]) - 1, threshold_pos, threshold_rot)

    return reduce_bone_frame_dic

# キーフレームを間引く
# オリジナル：https://github.com/errno-mmd/smoothvmd/blob/master/reducevmd.cc
def reduce_bone_frame(v, head, tail, threshold_pos, threshold_rot):
    # 移動のエラー最大値
    max_pos_err = float(0.0)
    # 回転のエラー最大値
    max_rot_err = float(0.0)
    # 移動：エラー最大値のindex
    max_idx_pos = 0
    # 回転：エラー最大値のindex
    max_idx_rot = 0
    # 最初から最後までのフレーム数
    total = tail - head

    for i in range(head + 1, tail , 1):
        # 移動
        ip_pos = v[head].position + (v[tail].position - v[head].position) * (i - head) / total
        pos_err = (ip_pos - v[i].position).length()

        if pos_err > max_pos_err:
            max_idx_pos = i
            max_pos_err = pos_err

        t = float(i - head) / total

        # 回転
        ip_rot = QQuaternion.slerp(v[head].rotation, v[tail].rotation, t)
        q_err = (ip_rot * v[i].rotation.inverted()).normalized()

        # フィルタではなく、ここで正負反転させてプラスに寄せる
        if q_err.scalar() < 0:
            q_err.setX(q_err.x() * -1)
            q_err.setY(q_err.y() * -1)
            q_err.setX(q_err.z() * -1)
            q_err.setScalar(q_err.scalar() * -1)
            
        #  math.acos(q_err.scalar()) * 2 * 180 / math.pi
        rot_err = math.degrees(math.acos(q_err.scalar()))
        # logger.info("rot_err: %s, %s", rot_err, max_rot_err)
        
        if rot_err > max_rot_err:
            max_idx_rot = i
            max_rot_err = rot_err

    v1 = []
    if max_pos_err > threshold_pos:
        v1 = reduce_bone_frame(v, head, max_idx_pos, threshold_pos, threshold_rot)
        v2 = reduce_bone_frame(v, max_idx_pos, tail, threshold_pos, threshold_rot)
        
        v1.extend(v2)
    else:
        if max_rot_err > threshold_rot:
            v1 = reduce_bone_frame(v, head, max_idx_rot, threshold_pos, threshold_rot)
            v2 = reduce_bone_frame(v, max_idx_rot, tail, threshold_pos, threshold_rot)

            v1.extend(v2)
        else:
            v1.append(v[head])

    return v1
