#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
from PyQt5.QtGui import QQuaternion, QVector4D, QVector3D, QMatrix4x4
import logging
import csv
import numpy as np
import math
import copy

import pos2vmd_utils

logger = logging.getLogger("__main__").getChild(__name__)

# 全身で最も直立している姿勢をいくつか返す
def calc_upright_body(bone_frame_dic):
    return calc_upright_bones(bone_frame_dic, ["上半身", "上半身2", "下半身", "左足", "左ひざ", "右足", "右ひざ"])

# 最も直立している姿勢をいくつか返す
def calc_upright_bones(bone_frame_dic, target_bones):

    # ソート用に新しく辞書を生成する
    upright_bones_dic = {}

    keys =[]
    values =[]
    for n in range(len(bone_frame_dic[target_bones[0]])):
        keys.append(bone_frame_dic[target_bones[0]][n].frame)
        angles = []
        for bone_name in target_bones:
            if len(bone_frame_dic[bone_name]) > n:
                eular = bone_frame_dic[bone_name][n].rotation.toEulerAngles()
                angles.append(abs(eular.x()))
                angles.append(abs(eular.y()))
                angles.append(abs(eular.z()))
        values.append( np.nanmax(angles) )

    # logger.info(keys)
    # logger.info(values)
    
    upright_bones_dic = dict(zip(keys, values))

    # オイラー角の絶対最大値昇順でソートする。NaNは無視する
    sorted_upright_bones_dic = sorted(upright_bones_dic.items(), key=lambda x: x[1])

    logger.debug("ソート後")
    logger.debug(sorted_upright_bones_dic[:100])

    upright_idxs = []
    for k, v in sorted_upright_bones_dic[:100]:
        if is_almost_same_idx(upright_idxs, k, 30):
            continue
        
        upright_idxs.append(k)

        if len(upright_idxs) >= 10:
            break
            

    # # 直立に近い順のボーンリスト
    # upright_bones = [[0 for i in range(len(target_bones))] for j in range(100)]
    # for n, bone_name in enumerate(target_bones):
    #     # 直立昇順のインデックスリストを生成する
    #     for m, bone in enumerate(calc_upright_bone(bone_name)):
    #         # 配列は持ち方逆転
    #         # 0: 直立に近い順のインデックス
    #         # 1: ボーンインデックス
    #         upright_bones[m][n] = bone.frame

    # for n, bones_parts in enumerate(upright_bones[:3]):
    #     for m, b in enumerate(bones_parts[:5]):
    #         logger.debug("ソート前: {0} {1}: {2}".format(n, m, b))

    # upright_bones_flat = np.array(upright_bones_dic).flatten()

    # # 直立っぽいのを検出する
    # most_common_idxs = Counter(sorted_upright_bones_dic.values()).most_common()
    # logger.info(most_common_idxs)

    # upright_idxs = []
    # for most_common_idx in most_common_idxs:
    #     # 0フレーム目は除外
    #     if most_common_idx[0] != 0 and is_almost_same_idx(upright_idxs, most_common_idx[0], 30) == False:
    #         upright_idxs.append(most_common_idx[0])

    #     if len(upright_idxs) >= 10:
    #         break

    return upright_idxs

def calc_upright_key(bones):

    # 指定フレームの全指定ボーンの回転角度
    bone_rotations = []
    for k, v in bones.values():
        bone_rotations.append(v)
    
    return np.nanmax(np.array(bone_rotations))


# ほぼ同じようなインデックスの場合TRUE
def is_almost_same_idx(idxs, n, app):
    for i in idxs:
        if abs(i - n) < app:
            return True

    return False

def calc_upright_bone(bone_frame_dic, bone_name):

    # ソート用に新しく配列を生成する
    upright_bones = []
    for bone in bone_frame_dic[bone_name]:
        upright_bones.append(copy.deepcopy(bone))

    logger.debug("ソート前: %s", bone_name)
    for n, b in enumerate(upright_bones[:10]):
        logger.debug("{0}: {1}, {2}, {3}".format(b.frame, b.rotation.x(), b.rotation.y(), b.rotation.z()))

    # オイラー角の絶対値合計値昇順でソートする。NaNは無視する
    upright_bones.sort(key=lambda x: np.nanmax(np.array([abs(x.rotation.toEulerAngles().x()), abs(x.rotation.toEulerAngles().y()), abs(x.rotation.toEulerAngles().z())]))) 

    logger.info("ソート後: %s", bone_name)
    for n, b in enumerate(upright_bones[:10]):
        logger.info("{0}: {1}, {2}, {3}".format(b.frame, b.rotation.toEulerAngles().x(), b.rotation.toEulerAngles().y(), b.rotation.toEulerAngles().z()))

    # # 1/300までのインデックスのみターゲットにする
    # upright_idxs = []
    # for n in range(round(len(bone_frame_dic[bone_name])/300)):
    #     upright_idxs.append(upright_bones[n])

    return upright_bones[:100]


# IKの計算
def calc_IK(bone_frame_dic, bone_csv_file, smoothed_2d, depth_all_frames, upright_idxs, heelpos):
    logger.debug("bone_csv_file: "+ bone_csv_file)

    upright_idx = upright_idxs[0]

    # ボーンファイルを開く
    with open(bone_csv_file, "r", encoding=pos2vmd_utils.get_file_encoding(bone_csv_file)) as bf:
        reader = csv.reader(bf)

        for row in reader:

            if row[1] == "下半身" or row[2].lower() == "lower body":
                # 下半身ボーン
                lower_body_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "左足" or row[2].lower() == "leg_l":
                # 左足ボーン
                left_leg_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "左ひざ" or row[2].lower() == "knee_l":
                # 左ひざボーン
                left_knee_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "左足首" or row[2].lower() == "ankle_l":
                # 左足首ボーン
                left_ankle_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "左つま先" or row[2].lower() == "l toe":
                # 左つま先ボーン
                left_toes_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "右足" or row[2].lower() == "leg_r":
                # 右足ボーン
                right_leg_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "右ひざ" or row[2].lower() == "knee_r":
                # 右ひざボーン
                right_knee_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "右足首" or row[2].lower() == "ankle_r":
                # 右足首ボーン
                right_ankle_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "右つま先" or row[2].lower() == "r toe":
                # 右つま先ボーン
                right_toes_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[0] == "Bone" and (row[1] == "左足ＩＫ" or row[2].lower() == "leg ik_l"):
                # 左足ＩＫボーン
                left_leg_ik_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[0] == "Bone" and (row[1] == "右足ＩＫ" or row[2].lower() == "leg ik_r"):
                # 右足ＩＫボーン
                right_leg_ik_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "センター" or row[2].lower() == "center":
                # センターボーン
                center_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

    # 2Dの直立フレームの腰の位置
    center_upright_2d_y = (smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["RHip"]].y() + smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["LHip"]].y()) / 2

    # 前回フレーム
    prev_left_frame = 0
    prev_right_frame = 0

    for n in range(len(bone_frame_dic["左足"])):
        logger.debug("足IK計算 frame={0}".format(n))
        # logger.debug("右足踵={0}, 左足踵={1}".format(smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["RAnkle"]], smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["LAnkle"]]))

        # logger.debug("前回左x={0}, 今回左x={1}, 差分={2}".format(smoothed_2d[prev_left_frame][4].x(), smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["LAnkle"]].x(), abs(np.diff([smoothed_2d[prev_left_frame][4].x(), smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["LAnkle"]].x()]))))
        # logger.debug("前回左y={0}, 今回左y={1}, 差分={2}".format(smoothed_2d[prev_left_frame][4].y(), smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["LAnkle"]].y(), abs(np.diff([smoothed_2d[prev_left_frame][4].y(), smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["LAnkle"]].y()]))))

        #左足IK
        if n > 0 and abs(np.diff([smoothed_2d[prev_left_frame][pos2vmd_utils.SMOOTHED_2D_INDEX["LAnkle"]].x(), smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["LAnkle"]].x()])) < 5 and abs(np.diff([smoothed_2d[prev_left_frame][pos2vmd_utils.SMOOTHED_2D_INDEX["LAnkle"]].y(), smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["LAnkle"]].y()])) < 5:
            # ほぼ動いていない場合、前回分をコピー
            # logger.debug("前回左IKコピー")

            # 前回からほぼ動いていない場合、前回の値をコピーする
            left_ankle_pos = bone_frame_dic["左足ＩＫ"][prev_left_frame].position
            left_ik_rotation = bone_frame_dic["左足ＩＫ"][prev_left_frame].rotation
            left_leg_diff_rotation = bone_frame_dic["左足"][prev_left_frame].rotation
        else:
            # 前回から動いている場合、計算する
            # 左足IK
            (left_ankle_pos, left_ik_rotation, left_leg_diff_rotation) = \
                calc_IK_matrix(center_bone, lower_body_bone, left_leg_bone, left_knee_bone, left_ankle_bone, left_toes_bone, left_leg_ik_bone \
                    , bone_frame_dic["センター"][n].position \
                    , bone_frame_dic["下半身"][n].rotation, bone_frame_dic["左足"][n].rotation, bone_frame_dic["左ひざ"][n].rotation )

            # 前回登録フレームとして保持
            prev_left_frame = n

        # logger.debug("前回右x={0}, 今回右x={1}, 差分={2}".format(smoothed_2d[prev_left_frame][3].x(), smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["RAnkle"]].x(), abs(np.diff([smoothed_2d[prev_left_frame][3].x(), smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["RAnkle"]].x()]))))
        # logger.debug("前回右y={0}, 今回右y={1}, 差分={2}".format(smoothed_2d[prev_left_frame][3].y(), smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["RAnkle"]].y(), abs(np.diff([smoothed_2d[prev_left_frame][3].y(), smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["RAnkle"]].y()]))))
            
        # 右足IK
        if n > 0 and abs(np.diff([smoothed_2d[prev_right_frame][pos2vmd_utils.SMOOTHED_2D_INDEX["RAnkle"]].x(), smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["RAnkle"]].x()])) < 5 and abs(np.diff([smoothed_2d[prev_right_frame][pos2vmd_utils.SMOOTHED_2D_INDEX["RAnkle"]].y(), smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["RAnkle"]].y()])) < 5:
            # ほぼ動いていない場合、前回分をコピー
            # logger.debug("前回右IKコピー")

            right_ankle_pos = bone_frame_dic["右足ＩＫ"][prev_right_frame].position
            right_ik_rotation = bone_frame_dic["右足ＩＫ"][prev_right_frame].rotation
            right_leg_diff_rotation = bone_frame_dic["右足"][prev_right_frame].rotation
        else:          
            # 右足IK
            (right_ankle_pos, right_ik_rotation, right_leg_diff_rotation) = \
                calc_IK_matrix(center_bone, lower_body_bone, right_leg_bone, right_knee_bone, right_ankle_bone, right_toes_bone, right_leg_ik_bone \
                    , bone_frame_dic["センター"][n].position \
                    , bone_frame_dic["下半身"][n].rotation, bone_frame_dic["右足"][n].rotation, bone_frame_dic["右ひざ"][n].rotation )
            
            # 前回登録フレームとして保持
            prev_right_frame = n

        # 右足も左足も計算しなかった場合
        if n > 0 and prev_left_frame != n and prev_right_frame != n:
            # 前回インデックスで近い方採用
            prev_idx = prev_left_frame if prev_left_frame > prev_right_frame else prev_right_frame
            # センターZを動かさない
            # logger.info("n=%s, previdx=%s", n, prev_idx)
            # logger.info("z変更前=%s", bone_frame_dic["センター"][n].position.z())
            bone_frame_dic["センター"][n].position.setZ( bone_frame_dic["センター"][prev_idx].position.z() )
            # logger.info("z変更後=%s", bone_frame_dic["センター"][n].position.z())


        # 右足も左足も計算した場合
        # if prev_left_frame == prev_right_frame == n:

            # if heelpos != 0:
            #     # 踵位置補正がかかっている場合、補正を加算する
            #     left_ankle_pos.setY(left_ankle_pos.y() + heelpos)
            #     right_ankle_pos.setY(right_ankle_pos.y() + heelpos)
            #     bone_frame_dic["センター"][n].position.setY( bone_frame_dic["センター"][n].position.y() + heelpos )
        # elif prev_left_frame != n and prev_right_frame != n:
        #     # 固定位置が近い方のINDEXを取得する
        #     prev_idx = prev_left_frame if prev_left_frame <= prev_right_frame else prev_right_frame

        #     # 右足も左足も計算しなかった場合、センターをコピーする
        #     bone_frame_dic["センター"][n].position.setY( bone_frame_dic["センター"][prev_idx].position.y() )

        # logger.debug("left_ankle_pos:{0}, right_ankle_pos: {1}".format(left_ankle_pos, right_ankle_pos))

        # 両足IKがマイナスの場合(地面にめり込んでいる場合)
        if left_ankle_pos.y() < 0 and right_ankle_pos.y() < 0:
            ankle_pos_max = np.max([left_ankle_pos.y(), right_ankle_pos.y()])

            # logger.debug("ankle_pos_max:{0}".format(ankle_pos_max))    

            # logger.debug("center.y1:{0}".format(bone_frame_dic["センター"][n].position.y()))    

            # 足IKを地表にあげる
            left_ankle_pos.setY( left_ankle_pos.y() - ankle_pos_max )
            right_ankle_pos.setY( right_ankle_pos.y() - ankle_pos_max )

            # FIXME センターががくがくする？要調査
            bone_frame_dic["センター"][n].position.setY( bone_frame_dic["センター"][n].position.y() - ankle_pos_max )
            
            # logger.debug("center.y2:{0}".format(bone_frame_dic["センター"][n].position.y()))    

            # X回転もさせず、接地させる
            left_ik_rotation = QQuaternion.fromEulerAngles(0, left_ik_rotation.toEulerAngles().y(), left_ik_rotation.toEulerAngles().z() )
            right_ik_rotation = QQuaternion.fromEulerAngles(0, right_ik_rotation.toEulerAngles().y(), right_ik_rotation.toEulerAngles().z() )

        # FIXME ジャンプしてる時と浮いてる時の区別がつかないので、一旦保留        
        # if bone_frame_dic["センター"][n].position.y() > 0 \
        #     and left_ankle_pos.y() >= 0 and abs(left_ik_rotation.toEulerAngles().x()) < 20 and abs(left_ik_rotation.toEulerAngles().y()) < 20 and abs(left_ik_rotation.toEulerAngles().z()) < 20 \
        #     and right_ankle_pos.y() >= 0 and abs(right_ik_rotation.toEulerAngles().x()) < 20 and abs(right_ik_rotation.toEulerAngles().y()) < 20 and abs(right_ik_rotation.toEulerAngles().z()) < 20:
        #     # Y軸が浮いていて、かつ足の角度が小さい場合、下向きに補正

        #     # センターを補正
        #     new_center_y = 0 - ( ( left_ankle_pos.y() + right_ankle_pos.y() ) / 2 ) 
        #     # しゃがんでる場合、もともとセンターがマイナスの可能性があるので、その場合は上書きしない
        #     if bone_frame_dic["センター"][n].position.y() > new_center_y:
        #         logger.debug("浮きセンターY上書き n={0}, y={1}, new_y={2}".format(n, bone_frame_dic["センター"][n].position.y(), new_center_y))
        #         bone_frame_dic["センター"][n].position.setY(new_center_y)

        #     # Y軸はセンターマイナスで接地させる
        #     left_ankle_pos.setY(0)
        #     right_ankle_pos.setY(0)

        #     # X回転もさせず、接地させる
        #     left_ik_rotation.setX(0)
        #     right_ik_rotation.setX(0)

        if left_ankle_pos.y() < 0 and right_ankle_pos.y() >= 0:
            # センターが少ししゃがんでて、足が浮いている場合、下ろす
            # 左足だけの場合マイナス値は0に補正
            left_ankle_pos.setY(0)

            # X回転もさせず、接地させる
            left_ik_rotation = QQuaternion.fromEulerAngles(0, left_ik_rotation.toEulerAngles().y(), left_ik_rotation.toEulerAngles().z() )

        if (right_ankle_pos.y() < 0 and left_ankle_pos.y() >= 0):
            # 右足だけの場合マイナス値は0に補正
            right_ankle_pos.setY(0)

            # X回転もさせず、接地させる
            right_ik_rotation = QQuaternion.fromEulerAngles(0, right_ik_rotation.toEulerAngles().y(), right_ik_rotation.toEulerAngles().z() )

        # if abs(bone_frame_dic["上半身"][n].rotation.toEulerAngles().y()) < 30 and left_ankle_pos.y() == 0:
        #     # 正面向きでY位置が0の場合、回転させず、接地させる
        #     left_ik_rotation.setX(0)
        #     left_ik_rotation.setY(0)
        #     left_ik_rotation.setZ(0)

        # if abs(bone_frame_dic["上半身"][n].rotation.toEulerAngles().y()) < 30 and right_ankle_pos.y() == 0:
        #     # 正面向きでY位置が0の場合、回転させず、接地させる
        #     right_ik_rotation.setX(0)
        #     right_ik_rotation.setY(0)
        #     right_ik_rotation.setZ(0)

        # センターと足首までのY距離
        bone_center_ankle_y = center_bone[1] - right_ankle_bone[1]
        # logger.debug("bone_center_leg_y {0}".format(bone_center_leg_y))

        # 足IKの位置が0で、センターが沈んでいる場合、ボーンのセンター位置に合わせて少しずらす
        if ( abs(bone_frame_dic["センター"][n].position.y()) > bone_center_ankle_y ):
            new_center_y = bone_frame_dic["センター"][n].position.y() - ( center_bone[1] - right_leg_bone[1] )
            logger.debug("陥没センターY上書き n={0}, y={1}, new_y={2}".format(n, bone_frame_dic["センター"][n].position.y(), new_center_y))
            bone_frame_dic["センター"][n].position.setY(new_center_y)

        bone_frame_dic["左足ＩＫ"][n].position = left_ankle_pos
        bone_frame_dic["左足ＩＫ"][n].rotation = left_ik_rotation
        bone_frame_dic["左足"][n].rotation = left_leg_diff_rotation

        bone_frame_dic["右足ＩＫ"][n].position = right_ankle_pos
        bone_frame_dic["右足ＩＫ"][n].rotation = right_ik_rotation
        bone_frame_dic["右足"][n].rotation = right_leg_diff_rotation

        # if n >= 1800:
        #     sys.exit()

    #　ひざは登録除去
    bone_frame_dic["左ひざ"] = []
    bone_frame_dic["右ひざ"] = []

# IK回転の計算
def calc_IK_rotation(bone_frame_dic, bone_csv_file, positions_multi):
    logger.debug("bone_csv_file: "+ bone_csv_file)

    # ボーンファイルを開く
    with open(bone_csv_file, "r", encoding=pos2vmd_utils.get_file_encoding(bone_csv_file)) as bf:
        reader = csv.reader(bf)

        # とりあえず初期化
        lower_body_bone = QVector3D()
        left_leg_bone = QVector3D()
        left_knee_bone = QVector3D()
        left_ankle_bone = QVector3D()
        left_toes_bone = QVector3D()
        right_leg_bone = QVector3D()
        right_knee_bone = QVector3D()
        right_ankle_bone = QVector3D()
        right_toes_bone = QVector3D()
        left_leg_ik_bone = QVector3D()
        right_leg_ik_bone = QVector3D()
        center_bone = QVector3D()

        for row in reader:

            if row[1] == "下半身" or row[2].lower() == "lower body":
                # 下半身ボーン
                lower_body_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "左足" or row[2].lower() == "leg_l":
                # 左足ボーン
                left_leg_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "左ひざ" or row[2].lower() == "knee_l":
                # 左ひざボーン
                left_knee_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "左足首" or row[2].lower() == "ankle_l":
                # 左足首ボーン
                left_ankle_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "左つま先" or row[2].lower() == "l toe":
                # 左つま先ボーン
                left_toes_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "右足" or row[2].lower() == "leg_r":
                # 右足ボーン
                right_leg_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "右ひざ" or row[2].lower() == "knee_r":
                # 右ひざボーン
                right_knee_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "右足首" or row[2].lower() == "ankle_r":
                # 右足首ボーン
                right_ankle_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "右つま先" or row[2].lower() == "r toe":
                # 右つま先ボーン
                right_toes_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[0] == "Bone" and (row[1] == "左足ＩＫ" or row[2].lower() == "leg ik_l"):
                # 左足ＩＫボーン
                left_leg_ik_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[0] == "Bone" and (row[1] == "右足ＩＫ" or row[2].lower() == "leg ik_r"):
                # 右足ＩＫボーン
                right_leg_ik_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "センター" or row[2].lower() == "center":
                # センターボーン
                center_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

    for n in range(len(bone_frame_dic["左足"])):

        # 左足IK
        (_, left_ik_rotation, left_leg_diff_rotation) = \
            calc_IK_matrix(center_bone, lower_body_bone, left_leg_bone, left_knee_bone, left_ankle_bone, left_toes_bone, left_leg_ik_bone \
                , bone_frame_dic["センター"][n].position \
                , bone_frame_dic["下半身"][n].rotation, bone_frame_dic["左足"][n].rotation, bone_frame_dic["左ひざ"][n].rotation )

        # positionは、cal_IK_postionで計算した値を使用する
        left_ankle_pos = bone_frame_dic["左足ＩＫ"][n].position

        # 右足IK
        (_, right_ik_rotation, right_leg_diff_rotation) = \
            calc_IK_matrix(center_bone, lower_body_bone, right_leg_bone, right_knee_bone, right_ankle_bone, right_toes_bone, right_leg_ik_bone \
                , bone_frame_dic["センター"][n].position \
                , bone_frame_dic["下半身"][n].rotation, bone_frame_dic["右足"][n].rotation, bone_frame_dic["右ひざ"][n].rotation )

        right_ankle_pos = bone_frame_dic["右足ＩＫ"][n].position

        # 足が埋まっている場合 （TODO 足の接地の改善）
        if left_ankle_pos.y() < 0:
            left_ankle_pos.setY(0)
            # 膝が立っている場合
            if positions_multi[n][5].y() > 3:
                left_ik_rotation.setX(0)
        # 足が地面に近い場合
        elif left_ankle_pos.y() < 1:
            if positions_multi[n][5].y() > 3:
                left_ik_rotation.setX(left_ik_rotation.x()*left_ankle_pos.y())

        # 足が埋まっている場合
        if right_ankle_pos.y() < 0:
            right_ankle_pos.setY(0)
             # 膝が立っている場合
            if positions_multi[n][2].y() > 3:
                right_ik_rotation.setX(0)
        # 足が地面に近い場合
        elif right_ankle_pos.y() < 1:
            if positions_multi[n][2].y() > 3:
                right_ik_rotation.setX(right_ik_rotation.x()*right_ankle_pos.y())

        bone_frame_dic["左足ＩＫ"][n].position = left_ankle_pos
        bone_frame_dic["左足ＩＫ"][n].rotation = left_ik_rotation
        #bone_frame_dic["左足"][n].rotation = left_leg_diff_rotation

        bone_frame_dic["右足ＩＫ"][n].position = right_ankle_pos
        bone_frame_dic["右足ＩＫ"][n].rotation = right_ik_rotation
        #bone_frame_dic["右足"][n].rotation = right_leg_diff_rotation

    #　ひざは登録除去
    bone_frame_dic["左ひざ"] = []
    bone_frame_dic["右ひざ"] = []


# 行列でIKの位置を求める
def calc_IK_matrix(center_bone, lower_body_bone, leg_bone, knee_bone, ankle_bone, toes_bone, ik_bone, center_pos, lower_body_rotation, leg_rotation, knee_rotation):

    # logger.debug("calc_IK_matrix ------------------------")

    # IKを求める ----------------------------

    # ローカル位置
    trans_vs = [0 for i in range(6)]
    # センターのローカル位置
    trans_vs[0] = center_bone + center_pos - ik_bone
    # 下半身のローカル位置
    trans_vs[1] = lower_body_bone - center_bone
    # 足のローカル位置
    trans_vs[2] = leg_bone - lower_body_bone
    # ひざのローカル位置 
    trans_vs[3] = knee_bone - leg_bone
    # 足首のローカル位置
    trans_vs[4] = ankle_bone - knee_bone
    # つま先のローカル位置
    trans_vs[5] = toes_bone - ankle_bone
    
    # 加算用クォータニオン
    add_qs = [0 for i in range(6)]
    # センターの回転
    add_qs[0] = QQuaternion()
    # 下半身の回転
    add_qs[1] = lower_body_rotation
    # 足の回転
    add_qs[2] = leg_rotation
    # ひざの回転
    add_qs[3] = knee_rotation
    # 足首の回転
    add_qs[4] = QQuaternion()
    # つま先の回転
    add_qs[5] = QQuaternion()

    # 行列
    matrixs = [0 for i in range(6)]

    for n in range(len(matrixs)):
        # 行列を生成
        matrixs[n] = QMatrix4x4()
        # 移動
        matrixs[n].translate(trans_vs[n])
        # 回転
        matrixs[n].rotate(add_qs[n])

        # logger.debug("matrixs[n] n={0}".format(n))
        # logger.debug(matrixs[n])

    # 足付け根の位置
    leg_pos = matrixs[0] * matrixs[1] * QVector4D(trans_vs[2], 1)

    # logger.debug("leg_pos")
    # logger.debug(leg_pos.toVector3D())

    # ひざの位置
    knee_pos = matrixs[0] * matrixs[1] * matrixs[2] * QVector4D(trans_vs[3], 1)

    # logger.debug("knee_pos")
    # logger.debug(knee_pos.toVector3D())

    # 足首の位置(行列の最後は掛けない)
    ankle_pos = matrixs[0] * matrixs[1] * matrixs[2] * matrixs[3] * QVector4D(trans_vs[4], 1)
    # logger.debug("ankle_pos {0}".format(ankle_pos.toVector3D()))

    # logger.debug("ankle_pos")
    # logger.debug(ankle_pos.toVector3D())

    # つま先の位置
    toes_pos = matrixs[0] * matrixs[1] * matrixs[2] * matrixs[3] * matrixs[4] * QVector4D(trans_vs[5], 1)
    # logger.debug("toes_pos {0}".format(toes_pos.toVector3D()))

    # 足付け根から足首までの距離
    ankle_leg_diff = ankle_pos - leg_pos

    # logger.debug("ankle_leg_diff")
    # logger.debug(ankle_leg_diff)
    # logger.debug(ankle_leg_diff.length())

    # ひざから足付け根までの距離
    knee_leg_diff = knee_bone - leg_bone

    # logger.debug("knee_leg_diff")
    # logger.debug(knee_leg_diff)
    # logger.debug(knee_leg_diff.length())

    # 足首からひざまでの距離
    ankle_knee_diff = ankle_bone - knee_bone

    # logger.debug("ankle_knee_diff")
    # logger.debug(ankle_knee_diff)
    # logger.debug(ankle_knee_diff.length())

    # つま先から足首までの距離
    toes_ankle_diff = toes_bone - ankle_bone

    # logger.debug("toes_ankle_diff")
    # logger.debug(toes_ankle_diff)
    # logger.debug(toes_ankle_diff.length())

    # 三辺から角度を求める

    # 足の角度
    leg_angle = calc_leg_angle(ankle_leg_diff, knee_leg_diff, ankle_knee_diff)
    # logger.debug("leg_angle:   {0}".format(leg_angle))

    # ひざの角度
    knee_angle = calc_leg_angle(knee_leg_diff, ankle_knee_diff, ankle_leg_diff)
    # logger.debug("knee_angle:  {0}".format(knee_angle))

    # 足首の角度
    ankle_angle = calc_leg_angle(ankle_knee_diff, ankle_leg_diff, knee_leg_diff)
    # logger.debug("ankle_angle: {0}".format(ankle_angle))

    # 足の回転 ------------------------------

    # 足の付け根からひざへの方向を表す青い単位ベクトル(長さ1)
    # 足の付け根から足首へのベクトルをX軸回りに回転させる
    knee_v = QQuaternion.fromEulerAngles(leg_angle * -1, 0, 0) * ankle_leg_diff.toVector3D().normalized()

    # logger.debug("knee_v")
    # logger.debug(knee_v)

    # FKのひざの位置
    ik_knee_3d = knee_v * knee_leg_diff.length() + leg_pos.toVector3D()

    # logger.debug("ik_knee_3d")
    # logger.debug(ik_knee_3d)

    # IKのひざ位置からFKのひざ位置に回転させる
    leg_diff_rotation = QQuaternion.rotationTo(knee_pos.toVector3D(), ik_knee_3d)

    # logger.debug("leg_diff_rotation")
    # logger.debug(leg_diff_rotation)
    # logger.debug(leg_diff_rotation.toEulerAngles())

    # 足IKの回転（足首の角度）-------------------------

    # FKと同じ状態の足首の向き
    ik_rotation = lower_body_rotation * leg_rotation * knee_rotation
    # logger.debug("ik_rotation {0}".format(ik_rotation.toEulerAngles()))

    return (ankle_pos.toVector3D(), ik_rotation, leg_diff_rotation)



# 三辺から足の角度を求める
def calc_leg_angle(a, b, c):

    if a.length() == 0 or b.length() == 0:
        # 0割対策
        return 0

    cos = ( pow(a.length(), 2) + pow(b.length(), 2) - pow(c.length(), 2) ) / ( 2 * a.length() * b.length() )

    # logger.debug("cos")
    # logger.debug(cos)

    radian = np.arccos(cos)

    # logger.debug("radian")
    # logger.debug(radian)

    angle = np.rad2deg(radian)

    # logger.debug("angle")
    # logger.debug(angle)

    return angle

# センターZの計算 
def calc_center_z(bone_frame_dic, smoothed_2d, depths, start_frame, upright_idxs, center_xy_scale, center_z_scale, target_upright_idx, target_upright_depth, is_ik):

    if center_z_scale == 0:
        return

    # 直立インデックス 
    # upright_idx = upright_idxs[0]

    # 深度値の配列
    depth_values = {}
    for ds in depths:
        # ds = []
        # for pos in ["Neck"]:
        #     ds.append(d[pos2vmd_utils.DEPTH_INDEX[pos]])
        # logger.info(ds)
        # depth_values.append(np.average(np.array(ds[1:]), weights=[0.1,0.8,0.3,0.1,0.0,0.3,0.1,0.0,0.3,0.1,0.0,0.3,0.1,0.0,0.0,0.0,0.0,0.0]))
        # depth_values.append(ds[pos2vmd_utils.DEPTH_INDEX["Neck"]])
        # depth_values[int(ds[pos2vmd_utils.DEPTH_INDEX["index"]])] = ds[pos2vmd_utils.DEPTH_INDEX["Neck"]]
        depth_values[int(ds[pos2vmd_utils.DEPTH_INDEX["index"]])] = np.average([ds[pos2vmd_utils.DEPTH_INDEX["Neck"]],ds[pos2vmd_utils.DEPTH_INDEX["RHip"]],ds[pos2vmd_utils.DEPTH_INDEX["LHip"]]])
        # depth_values[int(ds[pos2vmd_utils.DEPTH_INDEX["index"]])] = np.average([ds[pos2vmd_utils.DEPTH_INDEX["RHip"]],ds[pos2vmd_utils.DEPTH_INDEX["LHip"]]])
        # depth_values.append(np.amax(np.array(ds[1:])))
        # depth_values.append(np.average(np.array(ds[1:]), weights=[0.1,0.6,0.1,0.1,0.0,0.1,0.1,0.0,0.5,0.1,0.0,0.5,0.1,0.0,0.0,0.0,0.0,0.0]))

    # logger.info("depth_values: %s", depth_values)

    # 全フレームの推定深度(あり得ない値を入れる)
    depth_all_frames = [-1000 for x in range(len(bone_frame_dic["センター"]))]

    if 0 not in depth_values:
        # 0F目から始まらない場合、0F目に先頭フレームの深度を設定する
        depth_all_frames[0] = depth_values[sorted(depth_values.keys())[0]]

    for n, d in enumerate(depth_all_frames):
        if n in depth_values:
            # 深度データがある場合、深度を設定する
            depth_all_frames[n] = float(depth_values[n])

            if n > 0:
                # 0以上の場合、過去フレームを埋める
                for m, pd in enumerate(depth_all_frames[0:n]):
                    if m > 0 and pd == -1000:
                        # 未設定の深度INDEXに辿り着いた場合
                        # logger.info("n: %s, m: %s, 区間: %s", n, m, n-m+1)
                        for o, nd in enumerate(np.linspace(depth_all_frames[m-1], depth_all_frames[n], (n-m+1))):
                            depth_all_frames[o+m] = nd
                        break

    # for idx, n in enumerate(depth_indexes) :
    #     # 深度のINDEX1件ごとにセンターZ計算
    #     nn = int(n)

    #     # 開始フレームインデックスまでは飛ばす
    #     if nn <= start_frame:
    #         continue

    #     # 現在の深度
    #     now_depth = depth_values[idx]

    #     # 深度リストに追加
    #     depth_all_frames.append(float(now_depth))

    #     if nn > 0:
    #         # 1F以降の場合、その間のセンターも埋める
    #         prev_depth = depth_values[idx - 1]
    #         prev_idx = int(depth_indexes[idx - 1])

    #         # 前回との間隔
    #         interval = nn - prev_idx

    #         # 前回との間隔の差分
    #         diff_depth = now_depth - prev_depth

    #         logger.debug("prev_idx: {0}, prev_depth: {1}, interval: {2}, diff_depth: {3}".format(prev_idx, prev_depth, interval, diff_depth))
            
    #         for midx, m in enumerate(range(prev_idx + 1, nn)):
    #             interval_depth = prev_depth + ( (diff_depth / interval) * (midx + 1) )

    #             # 深度リストに追加
    #             depth_all_frames.append(float(interval_depth))

    # logger.info("depth_all_frames: %s", depth_all_frames[2130:2145])

    # 深度を滑らかにする
    smoothed_depth_frames = smooth_depth(depth_all_frames, 13, 2)

    # logger.info("smoothed_depth_frames: %s", smoothed_depth_frames[2130:2145])
    # logger.info("len(smoothed_depth_frames): %s", len(smoothed_depth_frames))
    # logger.info("bone_frame_dic[センター]: %s", len(bone_frame_dic["センター"]))

    # 深度からセンターZを求める
    for idx, now_depth in enumerate(smoothed_depth_frames):
        if idx >= len(bone_frame_dic["センター"]):
            break

        # センターZ倍率から求める
        center_z = now_depth * center_z_scale
        logger.debug("idx: %s, now: %s, z:%s", idx, now_depth, center_z)

        # センターZ
        bone_frame_dic["センター"][idx].position.setZ(center_z)

    # 前回動いたフレーム
    prev_left_frame = 0
    prev_right_frame = 0

    logger.debug("calc_center_z 1: %s %s %s", bone_frame_dic["右足ＩＫ"][0].position.z(),  bone_frame_dic["左足ＩＫ"][0].position.z(), bone_frame_dic["センター"][0].position.z())

    # 左右足のどっちに接地しているか
    ik_ground_dic = {}

    for frame in range(len(bone_frame_dic["センター"])):
        # センターZを再調整
        left_leg_diff = bone_frame_dic["左足ＩＫ"][frame].position - bone_frame_dic["左足ＩＫ"][prev_left_frame].position
        if abs(left_leg_diff.x()) > 0.2 or abs(left_leg_diff.y()) > 0.2 or abs(left_leg_diff.z()) > 0.2:
            # 左足IKが前回から動いていたら、フレーム登録
            prev_left_frame = frame

        right_leg_diff = bone_frame_dic["右足ＩＫ"][frame].position - bone_frame_dic["右足ＩＫ"][prev_right_frame].position
        if abs(right_leg_diff.x()) > 0.2 or abs(right_leg_diff.y()) > 0.2 or abs(right_leg_diff.z()) > 0.2:
            # logger.info("右足ＩＫ: %s -> %s", bone_frame_dic["右足ＩＫ"][prev_right_frame].position, bone_frame_dic["右足ＩＫ"][frame].position)
            # 右足IKが前回から動いていたら、フレーム登録
            prev_right_frame = frame
    
        if prev_left_frame != frame and prev_right_frame != frame:
            # logger.info("センターZ動かさない: %s", frame)

            # 右足も左足も動いていない場合、センターZを前回から動かさない
            # 前回インデックスで近い方採用
            prev_idx = prev_left_frame if prev_left_frame > prev_right_frame else prev_right_frame
            bone_frame_dic["センター"][frame].position.setZ( bone_frame_dic["センター"][prev_idx].position.z() )

        if bone_frame_dic["左足ＩＫ"][frame].position.y() < bone_frame_dic["右足ＩＫ"][frame].position.y() or ( \
            bone_frame_dic["左足ＩＫ"][frame].position.y() > bone_frame_dic["右足ＩＫ"][frame].position.y() \
                and bone_frame_dic["左足ＩＫ"][frame - 1].position.y() < bone_frame_dic["右足ＩＫ"][frame - 1].position.y() \
                and bone_frame_dic["左足ＩＫ"][frame + 1].position.y() < bone_frame_dic["右足ＩＫ"][frame + 1].position.y() \
            ):
            # 左足が上か、1Fだけ右足が上の場合、左足接地と見なす
            ik_ground_dic[frame] = "left"
        else:
            # それ以外は右足接地
            ik_ground_dic[frame] = "right"

    for frame in range(1, len(bone_frame_dic["センター"]) - 1):
        if ik_ground_dic[frame] == "left":
            # 左足接地の場合
            # if 4380 < frame < 4430:
            # logger.info("○左足接地 %s: l: %s, r: %s", frame, bone_frame_dic["左足ＩＫ"][frame].position, bone_frame_dic["右足ＩＫ"][frame].position)
            
            is_ground = True
            for f in range(frame, len(bone_frame_dic["センター"])):
                if ik_ground_dic[f] == "left" and is_ground == True:
                    # 左足接地の場合、動かさない
                    left_leg_diff = bone_frame_dic["左足ＩＫ"][frame].position.z() - bone_frame_dic["左足ＩＫ"][f].position.z()
                else:
                    # 左足空中の場合、直前の差分をそのまま使う（センターZを動かす）
                    # 一旦空中に出たら、差分は新たに求めない
                    is_ground = False
                
                # if 4380 < f < 4430 and  4380 < frame < 4430:
                #     logger.info("g: %s, frame: %s, f: %s, left_leg_diff: %s, fp: %s, pos: %s", is_ground, frame, f, left_leg_diff, bone_frame_dic["左足ＩＫ"][frame].position.z(), bone_frame_dic["左足ＩＫ"][f].position.z())

                bone_frame_dic["左足ＩＫ"][f].position.setZ(bone_frame_dic["左足ＩＫ"][f].position.z() + left_leg_diff)
                bone_frame_dic["右足ＩＫ"][f].position.setZ(bone_frame_dic["右足ＩＫ"][f].position.z() + left_leg_diff)

        elif ik_ground_dic[frame] == "right":
            # 右足接地の場合
            # if 4380 < frame < 4430:
            # logger.info("●右足接地 %s: l: %s, r: %s", frame, bone_frame_dic["左足ＩＫ"][frame].position, bone_frame_dic["右足ＩＫ"][frame].position)
            
            is_ground = True
            for f in range(frame, len(bone_frame_dic["センター"])):
                if ik_ground_dic[f] == "right" and is_ground == True:
                    # 右足接地の場合、動かさない
                    right_leg_diff = bone_frame_dic["右足ＩＫ"][frame].position.z() - bone_frame_dic["右足ＩＫ"][f].position.z()
                else:
                    # 右足空中の場合、直前の差分をそのまま使う（センターZを動かす）
                    # 一旦空中に出たら、差分は新たに求めない
                    is_ground = False
                
                # logger.info("%s, frame: %s, f: %s, right_leg_diff: %s, pos: %s", bone_frame_dic["右足ＩＫ"][f].position.y() <= right_ik_ground_pos[f], frame, f, right_leg_diff, bone_frame_dic["右足ＩＫ"][f].position.z())

                bone_frame_dic["左足ＩＫ"][f].position.setZ(bone_frame_dic["左足ＩＫ"][f].position.z() + right_leg_diff)
                bone_frame_dic["右足ＩＫ"][f].position.setZ(bone_frame_dic["右足ＩＫ"][f].position.z() + right_leg_diff)

        # センターZは両足の間に再設定する
        bone_frame_dic["センター"][frame].position.setZ( np.average([bone_frame_dic["左足ＩＫ"][frame].position.z(), bone_frame_dic["右足ＩＫ"][frame].position.z()]) )

    # 0F目もセンターZは両足の間に再設定する
    bone_frame_dic["センター"][0].position.setZ( np.average([bone_frame_dic["左足ＩＫ"][0].position.z(), bone_frame_dic["右足ＩＫ"][0].position.z()]) )



    # for frame in range(len(bone_frame_dic["センター"])):
    #     # センターZを再調整
    #     if frame > 0:
    #         left_leg_diff = bone_frame_dic["左足ＩＫ"][frame].position - bone_frame_dic["左足ＩＫ"][prev_left_frame].position
    #         if left_leg_diff.x() > 0.2 or left_leg_diff.y() > 0.2 or left_leg_diff.z() > 0.2 :
    #             # logger.info("左足ＩＫ: %s -> %s", bone_frame_dic["左足ＩＫ"][prev_left_frame].position, bone_frame_dic["左足ＩＫ"][frame].position)
    #             # 左足IKが前回から動いていたら、フレーム登録
    #             prev_left_frame = frame

    #         right_leg_diff = bone_frame_dic["右足ＩＫ"][frame].position - bone_frame_dic["右足ＩＫ"][prev_right_frame].position
    #         if right_leg_diff.x() > 0.2 or right_leg_diff.y() > 0.2 or right_leg_diff.z() > 0.2 :
    #             # logger.info("右足ＩＫ: %s -> %s", bone_frame_dic["右足ＩＫ"][prev_right_frame].position, bone_frame_dic["右足ＩＫ"][frame].position)
    #             # 右足IKが前回から動いていたら、フレーム登録
    #             prev_right_frame = frame
            
    #         if prev_left_frame != frame and prev_right_frame != frame:
    #             # logger.info("センターZ動かさない: %s", frame)

    #             # 右足も左足も動いていない場合、センターZを前回から動かさない
    #             # 前回インデックスで近い方採用
    #             prev_idx = prev_left_frame if prev_left_frame > prev_right_frame else prev_right_frame
    #             bone_frame_dic["センター"][frame].position.setZ( bone_frame_dic["センター"][prev_idx].position.z() )

    # for frame in range(len(bone_frame_dic["センター"])):
    #     # 調整後のセンターZに足IKを合わせる
    #     if frame == 0:
    #         bone_frame_dic["左足ＩＫ"][frame].position.setZ(bone_frame_dic["左足ＩＫ"][frame].position.z() + bone_frame_dic["センター"][frame].position.z())
    #         bone_frame_dic["右足ＩＫ"][frame].position.setZ(bone_frame_dic["右足ＩＫ"][frame].position.z() + bone_frame_dic["センター"][frame].position.z())
    #     else:
    #         # IKのZを調整したか否か
    #         is_left_ik_z_adjust = False
    #         is_right_ik_z_adjust = False

    #         left_leg_diff = bone_frame_dic["左足ＩＫ"][frame].position - bone_frame_dic["左足ＩＫ"][frame - 1].position
    #         if left_leg_diff.x() > 0.2 or left_leg_diff.y() > 0.2 or left_leg_diff.z() > 0.2 :
    #             is_left_ik_z_adjust = True

    #         right_leg_diff = bone_frame_dic["右足ＩＫ"][frame].position - bone_frame_dic["右足ＩＫ"][frame - 1].position
    #         if right_leg_diff.x() > 0.2 or right_leg_diff.y() > 0.2 or right_leg_diff.z() > 0.2 :
    #             is_right_ik_z_adjust = True

    #         if is_left_ik_z_adjust == False or is_right_ik_z_adjust == False:
    #             # 足IKの調整をどちらか行っていない場合、センターZを動かさない
    #             bone_frame_dic["センター"][frame].position.setZ( bone_frame_dic["センター"][frame - 1].position.z() )
            
    #         # 判定をした後、調整する
    #         if is_left_ik_z_adjust == True:
    #             # 調整する場合、センターZを考慮する
    #             bone_frame_dic["左足ＩＫ"][frame].position.setZ(bone_frame_dic["左足ＩＫ"][frame].position.z() + bone_frame_dic["センター"][frame].position.z())
    #         else:
    #             # 調整しない場合、前フレームのZをコピーする
    #             bone_frame_dic["左足ＩＫ"][frame].position.setZ(bone_frame_dic["左足ＩＫ"][frame - 1].position.z())

    #         # 右足も同様に調整する
    #         if is_right_ik_z_adjust == True:
    #             bone_frame_dic["右足ＩＫ"][frame].position.setZ(bone_frame_dic["右足ＩＫ"][frame].position.z() + bone_frame_dic["センター"][frame].position.z())
    #         else:
    #             bone_frame_dic["右足ＩＫ"][frame].position.setZ(bone_frame_dic["右足ＩＫ"][frame - 1].position.z())

    #     # センターZは両足の間に再設定する
    #     bone_frame_dic["センター"][frame].position.setZ( np.average([bone_frame_dic["左足ＩＫ"][frame].position.z(), bone_frame_dic["右足ＩＫ"][frame].position.z()]) )


def smooth_depth(depth_all_frames, section, smooth_times):
    # 深度の位置円滑化
    for n in range(smooth_times):
        for frame in range(len(depth_all_frames)):
            if frame >= section:
                prev_f = depth_all_frames[frame - section]
                now_f = depth_all_frames[frame]

                for new_idx, new_f in enumerate(np.linspace(prev_f, now_f, section+1)):
                    idx = frame - section + new_idx
                    # logger.info("idx: %s, now_f: %s, new_f: %s", idx, depth_all_frames[idx], new_f)
                    depth_all_frames[idx] = new_f

    return depth_all_frames

def get_nearest_idx(target_list, num):
    """
    概要: リストからある値に最も近い値のINDEXを返却する関数
    @param target_list: データ配列
    @param num: 対象値
    @return 対象値に最も近い値のINDEX
    """

    # logger.debug(target_list)
    # logger.debug(num)

    # リスト要素と対象値の差分を計算し最小値のインデックスを取得
    idx = np.abs(np.asarray(target_list) - num).argmin()
    return idx

# センターの計算
def calc_center(bone_frame_dic, smoothed_2d, bone_csv_file, upright_idxs, center_xy_scale, center_z_scale, heelpos, target_upright_idx, target_start_pos):

    if center_xy_scale == 0:
        return

    logger.debug("bone_csv_file: "+ bone_csv_file)

    # 直立インデックス
    upright_idx = upright_idxs[0]    

    # ボーンファイルを開く
    with open(bone_csv_file, "r",  encoding=pos2vmd_utils.get_file_encoding(bone_csv_file)) as bf:
        reader = csv.reader(bf)

        for row in reader:

            if row[1] == "センター" or row[2].lower() == "center":
                # センターボーン
                center_3d = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "首" or row[2].lower() == "neck":
                # 首ボーン
                neck_3d = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "右足" or row[2].lower() == "leg_r":
                # 右足ボーン
                right_leg_3d = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "左足" or row[2].lower() == "leg_l":
                # 左足ボーン
                left_leg_3d = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "右足首" or row[2].lower() == "ankle_r":
                # 右足首ボーン
                right_ankle_3d = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "左足首" or row[2].lower() == "ankle_l":
                # 左足首ボーン
                left_ankle_3d = QVector3D(float(row[5]), float(row[6]), float(row[7]))

    # logger.debug("neck_3d")
    # logger.debug(neck_3d)
    # logger.debug("right_leg_3d")
    # logger.debug(right_leg_3d)
    # logger.debug("left_leg_3d")
    # logger.debug(left_leg_3d)
    # logger.debug("center_3d")
    # logger.debug(center_3d)

    # ボーン頂点からの三角形面積
    bone_upright_area = pos2vmd_utils.calc_triangle_area(neck_3d, right_leg_3d, left_leg_3d)

    # logger.debug("smoothed_2d[upright_idx]")
    # logger.debug(smoothed_2d[upright_idx])

    # 直立フレームの三角形面積
    smoothed_upright_area = pos2vmd_utils.calc_triangle_area(smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["Neck"]], smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["RHip"]], smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["LHip"]])

    # logger.debug("upright_area")
    # logger.debug(smoothed_upright_area)

    # ボーンと映像の三角形比率(スケール調整あり)
    upright_xy_scale = bone_upright_area / smoothed_upright_area * center_xy_scale

    # logger.debug("upright_scale")
    # logger.debug(upright_xy_scale)

    # 直立フレームの左足と右足の位置のY平均
    upright_leg_avg = abs((smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["RHip"]].y() + smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["LHip"]].y()) / 2)

    # 直立フレームの首・左足と右足の位置のX平均
    upright_neck_leg_x_avg = (smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["Neck"]].x() + smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["RHip"]].x() + smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["LHip"]].x()) / 3

    # 直立フレームの左足首と右足首の位置の平均
    upright_ankle_avg = abs((smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["RAnkle"]].y() + smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["LAnkle"]].y()) / 2)

    # logger.debug("upright_ankle_avg")
    # logger.debug(upright_ankle_avg)

    # ボーンの足首のY位置
    bone_anke_y = (right_ankle_3d[1] + left_ankle_3d[1]) / 2

    # logger.debug("bone_anke_y")
    # logger.debug(bone_anke_y)

    # 足首位置の比率(上半身のみでゼロ割対策)
    if upright_ankle_avg != 0:
        upright_ankle_scale = (bone_anke_y / upright_ankle_avg) * (center_xy_scale / 100)
    else:
        upright_ankle_scale = 0

    # # 上半身から首までの距離
    # neck_upright_distance = upper_body_3d.distanceToPoint(neck_3d)

    # # logger.debug("neck_upright_distance")
    # # logger.debug(neck_upright_distance)

    # # 上半身から左足までの距離
    # left_leg_upright_distance = upper_body_3d.distanceToPoint(left_leg_3d)

    # # logger.debug("left_leg_upright_distance")
    # # logger.debug(left_leg_upright_distance)

    # # 上半身から左足までの距離
    # right_leg_upright_distance = upper_body_3d.distanceToPoint(right_leg_3d)
    
    # logger.debug("right_leg_upright_distance")
    # logger.debug(right_leg_upright_distance)

    # 3Dでの首・左足・右足の投影三角形
    # pos_upright_area = calc_triangle_area(positions_multi[upright_idx][8], positions_multi[upright_idx][1], positions_multi[upright_idx][4])
    
    upright_adjust_neck_leg_x_avg = 0
    if target_start_pos["center"] != QVector3D():
        # 0F目で調整用POSが指定されているの場合、X差分を取得
        upright_adjust_neck_leg_x_avg = (target_start_pos["Neck"].x() + target_start_pos["RHip"].x() + target_start_pos["LHip"].x()) / 3
        logger.info("upright_adjust_neck_leg_x_avg %s", upright_adjust_neck_leg_x_avg)

    for n, smoothed in enumerate(smoothed_2d):
        logger.debug("センター計算 frame={0}".format(n))

        # 左足と右足の位置の小さい方
        ankle_min = np.min([smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["RAnkle"]].y(), smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["LAnkle"]].y()])

        # logger.debug("ankle_min")
        # logger.debug(ankle_min)

        # logger.debug("ankle_min * upright_ankle_scale")
        # logger.debug(ankle_min * upright_ankle_scale)

        # 左足と右足の位置の平均
        leg_avg = abs((smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["RHip"]].y() + smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["LHip"]].y()) / 2)
        
        # 足の上下差
        leg_diff = upright_leg_avg - leg_avg

        # Y軸移動(とりあえずセンター固定)
        center_y = (leg_diff * upright_xy_scale) - (ankle_min * upright_ankle_scale)

        # 踵補正を入れて設定する
        bone_frame_dic["センター"][n].position.setY(center_y + heelpos)
        # bone_frame_dic["センター"][n].position.setY((leg_diff * upright_xy_scale))
        
        # 首・左足・右足の中心部分をX軸移動
        x_avg = ((smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["Neck"]].x() + smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["RHip"]].x() + smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["LHip"]].x()) / 3) \
                    - upright_neck_leg_x_avg + upright_adjust_neck_leg_x_avg
        center_x = x_avg * upright_xy_scale

        bone_frame_dic["センター"][n].position.setX(center_x)

        logger.debug("center {0} x={1}, y={2}".format(n, center_x, center_y))

        # 現在の映像の三角形面積
        # now_smoothed_area = calc_triangle_area(smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["Neck"]], smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["RHip"]], smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["LHip"]])

        # logger.debug("smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["Neck"]]")
        # logger.debug(smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["Neck"]])

        # logger.debug("smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["RHip"]]")
        # logger.debug(smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["RHip"]])

        # logger.debug("smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["LHip"]]")
        # logger.debug(smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["LHip"]])

        # logger.debug("now_smoothed_area")
        # logger.debug(now_smoothed_area)

        # # 首の位置を上半身の傾きから求める
        # upper_slope = QQuaternion(0, 0, -1, 0).inverted() * bone_frame_dic["上半身"][n].rotation.normalized() * neck_upright_distance

        # # 左足の位置を下半身の傾きから求める
        # left_leg_slope = QQuaternion(0, 0.2, 1, 0).inverted() * bone_frame_dic["下半身"][n].rotation.normalized() * left_leg_upright_distance

        # # 右足の位置を下半身の傾きから求める
        # right_leg_slope = QQuaternion(0, -0.2, 1, 0).inverted() * bone_frame_dic["下半身"][n].rotation.normalized() * right_leg_upright_distance

        # # 現在のボーン構造の三角形面積
        # now_bone_area = calc_triangle_area(upper_slope.vector(), left_leg_slope.vector(), right_leg_slope.vector())
        
        # logger.debug("smoothed_upright_area")
        # logger.debug(smoothed_upright_area)

        # 3Dでの首・左足・右足の投影三角形
        # pos_now_area = calc_triangle_area(positions_multi[n][8], positions_multi[n][1], positions_multi[n][4])

        # logger.debug("positions_multi[n][8]")
        # logger.debug(positions_multi[n][8])
        # logger.debug("positions_multi[n][1]")
        # logger.debug(positions_multi[n][1])
        # logger.debug("positions_multi[n][4]")
        # logger.debug(positions_multi[n][4])

        # logger.debug("pos_upright_area")
        # logger.debug(pos_upright_area)

        # logger.debug("pos_now_area")
        # logger.debug(pos_now_area)

        # 3Dでの現在の縮尺
        # pos_scale = pos_now_area / pos_upright_area

        # logger.debug("pos_scale")
        # logger.debug(pos_scale)

        # logger.debug("pos_scale ** 2")
        # logger.debug(pos_scale ** 2)

        # 2Dでの首・左足・右足の投影三角形
        # smoothed_now_area = calc_triangle_area(smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["Neck"]], smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["RHip"]], smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["LHip"]])

        # logger.debug("smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["Neck"]]")    
        # logger.debug(smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["Neck"]])
        # logger.debug("smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["RHip"]]")    
        # logger.debug(smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["RHip"]])
        # logger.debug("smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["LHip"]]")    
        # logger.debug(smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["LHip"]])

        # logger.debug("smoothed_upright_area")
        # logger.debug(smoothed_upright_area)

        # logger.debug("smoothed_now_area")
        # logger.debug(smoothed_now_area)

        # 2Dでの現在の縮尺
        # smoothed_scale = smoothed_now_area / smoothed_upright_area

        # logger.debug("smoothed_scale")
        # logger.debug(smoothed_scale)

        # logger.debug("((1 - smoothed_scale) ** 2)")
        # logger.debug(((1 - smoothed_scale) ** 2))

        # Z軸移動位置の算出
        # now_z_scale = pos_scale * (1 - smoothed_scale)

        # logger.debug("now_z_scale")
        # logger.debug(now_z_scale)

        # logger.debug("now_z_scale * center_z_scale")
        # logger.debug(now_z_scale * center_z_scale)

        # Z軸の移動補正
        # bone_frame_dic["センター"][n].position.setZ(now_z_scale * center_z_scale)


        # # 上半身の各軸傾き具合
        # rx = bone_frame_dic["上半身"][n].rotation.toEulerAngles().x()
        # ry = bone_frame_dic["上半身"][n].rotation.toEulerAngles().y() * -1
        # rz = bone_frame_dic["上半身"][n].rotation.toEulerAngles().z() * -1

        # # 傾いたところの頂点：首（傾きを反転させて正面向いた形にする）
        # smoothed_upright_slope_neck = calc_slope_point(smoothed_2d[upright_idx][8], rx * -1, ry * -1, rz * -1)
        # # 傾いたところの頂点：左足
        # smoothed_upright_slope_left_leg = calc_slope_point(smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["RHip"]], rx * -1, ry * -1, rz * -1)
        # # 傾いたところの頂点：右足
        # smoothed_upright_slope_right_leg = calc_slope_point(smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["LHip"]], rx * -1, ry * -1, rz * -1)

        # # 傾きを反転させた直立面積
        # smoothed_upright_slope_area = calc_triangle_area(smoothed_upright_slope_neck, smoothed_upright_slope_left_leg, smoothed_upright_slope_right_leg)

        # logger.debug("smoothed_upright_slope_area")
        # logger.debug(smoothed_upright_slope_area)

        # logger.debug("smoothed_upright_area")
        # logger.debug(smoothed_upright_area)

        # # 直立の関節の回転分面積を現在の関節面積で割って、大きさの比率を出す
        # now_z_scale = smoothed_upright_slope_area / smoothed_upright_area

        # if n == 340 or n == 341:

        #     logger.debug("smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["Neck"]]")
        #     logger.debug(smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["Neck"]])

        #     logger.debug("smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["RHip"]]")
        #     logger.debug(smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["RHip"]])

        #     logger.debug("smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["LHip"]]")
        #     logger.debug(smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["LHip"]])

        #     logger.debug("smoothed_upright_slope_neck")
        #     logger.debug(smoothed_upright_slope_neck)

        #     logger.debug("smoothed_upright_slope_left_leg")
        #     logger.debug(smoothed_upright_slope_left_leg)

        #     logger.debug("smoothed_upright_slope_right_leg")
        #     logger.debug(smoothed_upright_slope_right_leg)

        #     logger.debug("smoothed_upright_slope_area")
        #     logger.debug(smoothed_upright_slope_area)

        # # 傾きの総数 - 各傾きの絶対値＝傾き具合
        # rsum = (90 - abs(rx)) + (90 - abs(90 - abs(ry))) + (90 - abs(rz))
        # # 360で割って、どれくらい傾いているか係数算出(1に近いほど正面向き)
        # rsum_scale = (180 / rsum) ** ( center_z_scale ** center_z_scale)

        # logger.debug("rx")
        # logger.debug(rx)

        # logger.debug("ry")
        # logger.debug(ry)

        # logger.debug("rz")
        # logger.debug(rz)

        # logger.debug("rsum")
        # logger.debug(rsum)

        # logger.debug("rsum_scale")
        # logger.debug(rsum_scale)

        # logger.debug("now_z_scale")
        # logger.debug(now_z_scale)
            
        # # 1より大きい場合、近くにある(マイナス)
        # # 1より小さい場合、遠くにある(プラス)
        # now_z_scale_pm = 1 - now_z_scale

        # logger.debug("now_z_scale_pm")
        # logger.debug(now_z_scale_pm)

        # logger.debug("now_z_scale_pm * rsum_scale")
        # logger.debug(now_z_scale_pm * rsum_scale)

        # if n < 20:
        # logger.debug("upper_slope")
        # logger.debug(upper_slope)
        # logger.debug(upper_slope.vector())

        # logger.debug("left_leg_slope")
        # logger.debug(left_leg_slope)
        # logger.debug(left_leg_slope.vector())

        # logger.debug("right_leg_slope")
        # logger.debug(right_leg_slope)
        # logger.debug(right_leg_slope.vector())

        # logger.debug("bone_upright_area")
        # logger.debug(bone_upright_area)

        # logger.debug("now_bone_area")
        # logger.debug(now_bone_area)

        # logger.debug("now_scale")
        # logger.debug(now_scale)

        # logger.debug("now_scale * center_scale")
        # logger.debug(now_scale * center_scale)

        # logger.debug("leg_avg")
        # logger.debug(leg_avg)
        
        # logger.debug("leg_diff")
        # logger.debug(leg_diff)
        
        # logger.debug("smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["Neck"]].x()")
        # logger.debug(smoothed_2d[upright_idx][pos2vmd_utils.SMOOTHED_2D_INDEX["Neck"]].x())
        
        # logger.debug("smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["Neck"]].x()")
        # logger.debug(smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["Neck"]].x())
        
        # logger.debug("smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["RHip"]].x()")
        # logger.debug(smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["RHip"]].x())
        
        # logger.debug("smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["LHip"]].x()")
        # logger.debug(smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["LHip"]].x())
        
        # logger.debug("((smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["Neck"]].x() + smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["RHip"]].x() + smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["LHip"]].x()) / 3)")
        # logger.debug(((smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["Neck"]].x() + smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["RHip"]].x() + smoothed_2d[n][pos2vmd_utils.SMOOTHED_2D_INDEX["LHip"]].x()) / 3))
        
        # logger.debug("x_avg")
        # logger.debug(x_avg)

        # logger.debug("now_smoothed_area")
        # logger.debug(now_smoothed_area)

        # logger.debug("now_position_area")
        # logger.debug(now_position_area)

        # logger.debug("now_scale")
        # logger.debug(now_scale)

        # logger.debug("now_scale * upright_position_scale")
        # logger.debug(now_scale * upright_position_scale)

        

        # # モデルの上半身の傾き
        # upper_body_euler = QVector3D(
        #     bone_frame_dic["上半身"][n].rotation.toEulerAngles().x() \
        #     , bone_frame_dic["上半身"][n].rotation.toEulerAngles().y() * -1 \
        #     , bone_frame_dic["上半身"][n].rotation.toEulerAngles().z() * -1 \
        # ) 



        # # モデルの上半身の傾き。初期位置からフレームの位置まで回転
        # upper_body_qq = QQuaternion(0, upper_body_3d)
        # # upper_body_qq = QQuaternion.rotationTo( upper_body_3d, bone_frame_dic["上半身"][n].rotation.vector() )

        # if n < 20:
        #     logger.debug("bone_frame_dic")
        #     logger.debug(bone_frame_dic["上半身"][n].rotation)
        #     logger.debug(bone_frame_dic["上半身"][n].rotation.toVector4D())
        #     logger.debug(bone_frame_dic["上半身"][n].rotation.toEulerAngles())
        #     v = bone_frame_dic["上半身"][n].rotation.toVector4D()
        #     logger.debug(v.x() * v.w())
        #     logger.debug(v.y() * v.w() * -1)
        #     logger.debug(v.z() * v.w() * -1)
        #     logger.debug("upper_body_qq")
        #     logger.debug(upper_body_qq)
        #     logger.debug(upper_body_qq.toEulerAngles())
        #     logger.debug(upper_body_qq.toVector4D())


# センターと足IKの位置をpos.txtデータから計算
def calc_center_ik_position(bone_frame_dic, positions_multi, bone_csv_file, smoothed_2d, heelpos, is_ik):
    # ボーンファイルを開く
    with open(bone_csv_file, "r",  encoding=pos2vmd_utils.get_file_encoding(bone_csv_file)) as bf:
        reader = csv.reader(bf)

        # とりあえず初期化
        left_leg_bone = QVector3D()
        left_knee_bone = QVector3D()
        left_ankle_bone = QVector3D()
        right_leg_bone = QVector3D()
        right_knee_bone = QVector3D()
        right_ankle_bone = QVector3D()

        for row in reader:
            if row[1] == "左足" or row[2].lower() == "leg_l":
                # 左足ボーン
                left_leg_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "左ひざ" or row[2].lower() == "knee_l":
                # 左ひざボーン
                left_knee_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "左足首" or row[2].lower() == "ankle_l":
                # 左足首ボーン
                left_ankle_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "右足" or row[2].lower() == "leg_r":
                # 右足ボーン
                right_leg_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "右ひざ" or row[2].lower() == "knee_r":
                # 右ひざボーン
                right_knee_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

            if row[1] == "右足首" or row[2].lower() == "ankle_r":
                # 右足首ボーン
                right_ankle_bone = QVector3D(float(row[5]), float(row[6]), float(row[7]))

    # MMD上の両足の長さ（RHip-RKnee-RAnkle, LHip-LKnee-LAnkle）を計算
    mmd_leg_length = (right_ankle_bone-right_knee_bone).length() + (right_knee_bone-right_leg_bone).length() \
                   + (left_ankle_bone-left_knee_bone).length() + (left_knee_bone-left_leg_bone).length()

    # 左右方向のmmdとbaselineのスケール比率は、固定値とする
    scale_mmd_base_const = 18.83 / 1743 # = ミクさんの両足の長さ(18.83ミクセル:1506mm)/教師データの両足の長さ平均(1743mm)

    # 上下方向のスケール比率は、pos.txtの足の長さに合わせて変動値とする
    # pos.txtの両足の長さ（RHip-RKnee-RAnkle, LHip-LKnee-LAnkle）
    base_leg_length = []
    for frame, positions in enumerate(positions_multi):
        # 3dBaseLineでの足の長さ合計（RHip-RKnee-RAnkle, LHip-LKnee-LAnkle）を計算
        base_leg_length.append( (positions[3] - positions[2]).length() + (positions[2] - positions[1]).length()
                                + (positions[6] - positions[5]).length() + (positions[5] - positions[4]).length()
                              )
    # 前後の計91フレームで移動平均をとる
    move_ave_base_leg_length = calc_move_average(base_leg_length, 91)

    # 平均 
    ave_base_leg_length = np.mean(base_leg_length)

    # pos.txtのyは接地時の足首の位置を0としているため、その分のバイアス
    bias_y = (left_ankle_bone + right_ankle_bone)/2

    # 前回フレーム
    prev_left_frame = 0
    prev_right_frame = 0

    for frame, positions in enumerate(positions_multi):
        base_leg = move_ave_base_leg_length[frame]
        # pos.txtの足の長さが正しく取れない時のため、上限、下限を設ける
        if base_leg < ave_base_leg_length * 0.9:
            base_leg = ave_base_leg_length * 0.9
        if base_leg > ave_base_leg_length * 1.1:
            base_leg = ave_base_leg_length * 1.1

        # MMD上の足の長さと3dBaseLine上の足の長さの比率
        scale_mmd_base = mmd_leg_length/base_leg

        # センターIK
        hip_pos = QVector3D(scale_mmd_base_const * positions[0].x(),
                            scale_mmd_base * positions[0].y(),
                            scale_mmd_base_const * positions[0].z()
                        )
        hip_mmd = bias_y + hip_pos
        hip_mmd_diff = hip_mmd - (left_leg_bone + right_leg_bone)/2
        # 踵補正を入れて設定する
        heelpos_common = -0.2 # 0.2沈める
        hip_mmd_diff.setY(hip_mmd_diff.y() + heelpos_common + heelpos)
        bone_frame_dic["センター"][frame].position = hip_mmd_diff

        if is_ik:
            # 右足IK
            right_ankle_pos = QVector3D(scale_mmd_base_const * positions[3].x(),
                                        scale_mmd_base * positions[3].y(),
                                        scale_mmd_base_const * positions[3].z()
                                )
            right_ankle_mmd = bias_y + right_ankle_pos
            right_ankle_mmd_diff = right_ankle_mmd - right_ankle_bone
            # 踵補正を入れて設定する
            right_ankle_mmd_diff.setY(right_ankle_mmd_diff.y() + heelpos_common + heelpos)

            # 左足IK
            left_ankle_pos = QVector3D(scale_mmd_base_const * positions[6].x(),
                                        scale_mmd_base * positions[6].y(),
                                        scale_mmd_base_const * positions[6].z()
                                )
            left_ankle_mmd = bias_y + left_ankle_pos
            left_ankle_mmd_diff = left_ankle_mmd - left_ankle_bone
            # 踵補正を入れて設定する
            left_ankle_mmd_diff.setY(left_ankle_mmd_diff.y() + heelpos_common + heelpos)

            # 足止め処理
            if frame == 0:
                # 0F目の場合、そのまま前回分として保持
                bone_frame_dic["右足ＩＫ"][frame].position = right_ankle_mmd_diff
                bone_frame_dic["左足ＩＫ"][frame].position = left_ankle_mmd_diff
            else:
                if abs(np.diff([smoothed_2d[prev_left_frame][pos2vmd_utils.SMOOTHED_2D_INDEX["LAnkle"]].x(), smoothed_2d[frame][pos2vmd_utils.SMOOTHED_2D_INDEX["LAnkle"]].x()])) < 10 and abs(np.diff([smoothed_2d[prev_left_frame][pos2vmd_utils.SMOOTHED_2D_INDEX["LAnkle"]].y(), smoothed_2d[frame][pos2vmd_utils.SMOOTHED_2D_INDEX["LAnkle"]].y()])) < 10:
                    #左足IKが前回からほとんど動いていない場合、前回からコピーする
                    bone_frame_dic["左足ＩＫ"][frame].position = copy.deepcopy(bone_frame_dic["左足ＩＫ"][prev_left_frame].position)
                else:
                    # 動いている場合、前回計算フレームとして保持
                    prev_left_frame = frame
                    bone_frame_dic["左足ＩＫ"][frame].position = left_ankle_mmd_diff

                if abs(np.diff([smoothed_2d[prev_right_frame][pos2vmd_utils.SMOOTHED_2D_INDEX["RAnkle"]].x(), smoothed_2d[frame][pos2vmd_utils.SMOOTHED_2D_INDEX["RAnkle"]].x()])) < 10 and abs(np.diff([smoothed_2d[prev_right_frame][pos2vmd_utils.SMOOTHED_2D_INDEX["RAnkle"]].y(), smoothed_2d[frame][pos2vmd_utils.SMOOTHED_2D_INDEX["RAnkle"]].y()])) < 10:
                    #右足IKが前回からほとんど動いていない場合、前回からコピーする
                    bone_frame_dic["右足ＩＫ"][frame].position = copy.deepcopy(bone_frame_dic["右足ＩＫ"][prev_right_frame].position)
                else:
                    # 動いている場合、前回計算フレームとして保持
                    prev_right_frame = frame
                    bone_frame_dic["右足ＩＫ"][frame].position = right_ankle_mmd_diff



def calc_move_average(data, n):
    if len(data) > n:
        move_avg = np.convolve(data, np.ones(n)/n, 'valid')
        # 移動平均でデータ数が減るため、前と後ろに同じ値を繰り返しで補填する
        fore_n = int((n - 1)/2)
        back_n = n - 1 - fore_n
        result = np.hstack((np.tile([move_avg[0]], fore_n), move_avg, np.tile([move_avg[-1]], back_n)))
    else:
        avg = np.mean(data)
        result = np.tile([avg], len(data))

    return result
