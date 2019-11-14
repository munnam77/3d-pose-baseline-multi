#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# pos2vmd.py - convert joint position data to VMD

from __future__ import print_function

from PyQt5.QtGui import QQuaternion, QVector4D, QVector3D, QMatrix4x4
import os
import re
import argparse
import logging
import datetime
import numpy as np
import csv

from VmdWriter import VmdBoneFrame, VmdInfoIk, VmdShowIkFrame, VmdWriter
import pos2vmd_utils
import pos2vmd_calc
import pos2vmd_frame
import pos2vmd_filter
import pos2vmd_reduce
              
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

level = {0:logging.ERROR,
            1:logging.WARNING,
            2:logging.INFO,
            3:logging.DEBUG}
verbose = 2

# ディクショナリ型で各ボーンごとのキーフレームリストを作成する
bone_frame_dic = {
    "上半身":[],
    "上半身2":[],
    "下半身":[],
    "首":[],
    "頭":[],
    "左肩":[],
    "左腕":[],
    "左ひじ":[],
    "右肩":[],
    "右腕":[],
    "右ひじ":[],
    "左足":[],
    "左ひざ":[],
    "右足":[],
    "右ひざ":[],
    "センター":[],
    "グルーブ":[],
    "左足ＩＫ":[],
    "右足ＩＫ":[]
}

# 関節位置情報のリストからVMDを生成します
def position_list_to_vmd_multi(positions_multi, positions_gan_multi, upright_file, vmd_file, smoothed_file, bone_csv_file, depth_file, start_frame_file, center_xy_scale, center_z_scale, smooth_times, threshold_pos, threshold_rot, is_ik, heelpos, upright_target):
    # トレースモデル
    logger.info("トレースモデル: %s", bone_csv_file)

    # 開始フレームインデックス
    start_frame = pos2vmd_utils.load_start_frame(start_frame_file)
    logger.info("開始フレームインデックス: %d", start_frame)
    
    # 関節二次元情報を読み込み
    smoothed_2d = pos2vmd_utils.load_smoothed_2d(smoothed_file)

    # 上半身2があるかチェック
    is_upper2_body = pos2vmd_utils.is_upper2_body_bone(bone_csv_file)

    logger.info("傾きモーション読み込み開始 上半身2: %s", is_upper2_body)

    # 傾きをひじ用読み込み
    slope_motion = pos2vmd_utils.load_slope_vmd(is_upper2_body)

    # # Baseline側で前傾補正している前提でVMD側では前傾補正しない
    # slope_motion = None

    logger.info("角度計算開始")

    # 各関節角度の算出
    for frame, positions in enumerate(positions_multi):
        positions_gan = None
        if positions_gan_multi is not None:
            positions_gan = positions_gan_multi[frame]

        pos2vmd_frame.position_to_frame(bone_frame_dic, positions, positions_gan, smoothed_2d, frame, is_upper2_body, slope_motion)   

    logger.info("直立フレーム推定開始")

    # 体幹的に最も直立しているINDEX抽出
    upright_idxs = pos2vmd_calc.calc_upright_body(bone_frame_dic)

    logger.info(upright_idxs)

    logger.info("センター計算開始")

    # センター調整
    target_upright_idx, target_upright_depth, target_start_pos = pos2vmd_utils.load_upright_target(upright_target)

    # センターの計算
    # pos2vmd_calc.calc_center(bone_frame_dic, smoothed_2d, bone_csv_file, upright_idxs, center_xy_scale, center_z_scale, heelpos, target_upright_idx, target_start_pos)

    logger.info("IK計算開始")

    # センターと足のIKポジションの計算
    pos2vmd_calc.calc_center_ik_position(bone_frame_dic, positions_multi, bone_csv_file, smoothed_2d, heelpos, is_ik)

    if is_ik:
        # IKの計算
        # pos2vmd_calc.calc_IK(bone_frame_dic, bone_csv_file, smoothed_2d, depth_all_frames, upright_idxs, heelpos)

        # IK回転の計算
        pos2vmd_calc.calc_IK_rotation(bone_frame_dic, bone_csv_file, positions_multi)
    else:
        #　IKでない場合は登録除去
        bone_frame_dic["左足ＩＫ"] = []
        bone_frame_dic["右足ＩＫ"] = []

    depths = pos2vmd_utils.load_depth(depth_file)

    if depths is not None and center_z_scale > 0:
        # 深度ファイルがあり、スケールが指定されている場合のみ、Z軸計算
        logger.info("センターZ計算開始")

        # センターZの計算
        pos2vmd_calc.calc_center_z(bone_frame_dic, smoothed_2d, depths, start_frame, upright_idxs, center_xy_scale, center_z_scale, target_upright_idx, target_upright_depth, is_ik)

    # 直立関連ファイルに情報出力
    # 直立IDX
    upright_file.write(str(upright_idxs[0]))
    upright_file.write("\n")
    # 先頭フレームのセンターpos
    center_pos = bone_frame_dic["センター"][0].position
    upright_file.write("center,{0},{1},{2}".format(center_pos.x(), center_pos.y(), center_pos.z()))
    upright_file.write("\n")
    # 先頭フレームの2D
    # logger.info("upright: %s", upright_idxs[0])
    for key in ["Neck", "RHip", "LHip", "RKnee", "LKnee", "RAnkle", "LAnkle"]:
        # logger.info("key: %s, v: %s", k, v)
        s2d = smoothed_2d[0][pos2vmd_utils.SMOOTHED_2D_INDEX[key]]
        # logger.info(s2d)
        upright_file.write("{0},{1},{2},{3}".format(key, s2d.x(), s2d.y(), s2d.z()))
        upright_file.write("\n")

    upright_file.close()

    # グルーブ移管
    is_groove = pos2vmd_utils.set_groove(bone_frame_dic, bone_csv_file)

    if is_groove:
        logger.info("グルーブ移管")

    if smooth_times > 0:
        logger.info("円滑化開始")
        pos2vmd_filter.smooth_filter(bone_frame_dic, is_groove, smooth_times)

    if threshold_pos == 0 and threshold_rot == 0:
        # FULLキーVMD出力
        logger.info("FULL VMD出力開始")
        full_vmd_file = pos2vmd_utils.output_vmd(bone_frame_dic, vmd_file, upright_idxs, is_ik, "full")
        logger.info("FULL VMDファイル出力完了: {0}".format(full_vmd_file))
    else:
        # 間引き後キーVMD出力
        logger.info("間引き開始")
        reduce_bone_frame_dic = pos2vmd_reduce.reduce_frames(bone_frame_dic, is_groove, threshold_pos, threshold_rot)

        logger.info("間引き VMD出力開始")
        reduce_vmd_file = pos2vmd_utils.output_vmd(reduce_bone_frame_dic, vmd_file, upright_idxs, is_ik, "reduce")
        logger.info("間引き VMDファイル出力完了: {0}".format(reduce_vmd_file))



def position_multi_file_to_vmd(position_file, position_gan_file, upright_file, vmd_file, smoothed_file, bone_csv_file, depth_file, start_frame_file, center_xy_scale, center_z_scale, smooth_times, threshold_pos, threshold_rot, is_ik, heelpos, upright_target):
    positions_multi = pos2vmd_utils.read_positions_multi(position_file)
    
    # 3dpose-gan がない場合はNone
    if os.path.exists(position_gan_file):
        positions_gan_multi = pos2vmd_utils.read_positions_multi(position_gan_file)
    else:
        positions_gan_multi = None

    position_list_to_vmd_multi(positions_multi, positions_gan_multi, upright_file, vmd_file, smoothed_file, bone_csv_file, depth_file, start_frame_file, center_xy_scale, center_z_scale, smooth_times, threshold_pos, threshold_rot, is_ik, heelpos, upright_target)
    

if __name__ == '__main__':
    import sys
    if (len(sys.argv) < 13):
        logger.error("引数不足")

    parser = argparse.ArgumentParser(description='3d-pose-baseline to vmd')
    parser.add_argument('-t', '--target', dest='target', type=str,
                        help='target directory (3d-pose-baseline-vmd)')
    parser.add_argument('-u', '--upright-target', dest='upright_target', type=str,
                        default='',
                        help='upright target directory')
    parser.add_argument('-b', '--bone', dest='bone', type=str,
                        help='target model bone csv')
    parser.add_argument('-v', '--verbose', dest='verbose', type=int,
                        default=2,
                        help='logging level')
    parser.add_argument('-c', '--center-xyscale', dest='centerxy', type=int,
                        default=0,
                        help='center scale')
    parser.add_argument('-z', '--center-z-scale', dest='centerz', type=float,
                        default=0,
                        help='center z scale')
    parser.add_argument('-s', '--smooth-times', dest='smooth_times', type=int,
                        default=1,
                        help='smooth times')
    parser.add_argument('-p', '--move-reduce-pos', dest='threshold_pos', type=float,
                        default=0,
                        help='move bone reduce threshold')
    parser.add_argument('-r', '--move-reduce-rot', dest='threshold_rot', type=float,
                        default=0,
                        help='rotation bone reduce threshold')
    parser.add_argument('-k', '--leg-ik', dest='legik', type=int,
                        default=1,
                        help='leg ik')
    parser.add_argument('-e', '--heel position', dest='heelpos', type=float,
                        default=0,
                        help='heel position correction')
    args = parser.parse_args()

    # resultディレクトリだけ指定させる
    base_dir = args.target

    is_ik = True if args.legik == 1 else False

    # 入力と出力のファイル名は固定
    position_file = base_dir + "/pos.txt"
    smoothed_file = base_dir + "/smoothed.txt"
    depth_file = base_dir + "/depth.txt"
    start_frame_file = base_dir + "/start_frame.txt"

    # 3dpose-gan のposファイル。（ない可能性あり）
    position_gan_file = base_dir + "/pos_gan.txt"

    suffix = ""

    # ganは使用しない
    # if os.path.exists(position_gan_file) == False:
    #     suffix = "_ganなし"
    
    # ボーンCSVファイル名・拡張子
    bone_filename, bone_fileext = os.path.splitext(os.path.basename(args.bone))

    if os.path.exists(depth_file) == False:
        suffix = "{0}_depthなし".format(suffix)
    
    if is_ik == False:
        suffix = "{0}_FK".format(suffix)
    
    # 踵位置補正
    suffix = "{0}_h{1}".format(suffix, str(args.heelpos))
    
    # センターXY
    # suffix = "{0}_xy{1}".format(suffix, str(args.centerxy))

    # センターZ        
    suffix = "{0}_z{1}".format(suffix, str(args.centerz))

    # 円滑化回数
    suffix = "{0}_s{1}".format(suffix, str(args.smooth_times))
    
    # 移動間引き
    suffix = "{0}_p{1}".format(suffix, str(args.threshold_pos))
    
    # 回転間引き
    suffix = "{0}_r{1}".format(suffix, str(args.threshold_rot))
    
    vmd_file = "{0}/{3}_{1:%Y%m%d_%H%M%S}{2}_[type].vmd".format(base_dir, datetime.datetime.now(), suffix, bone_filename)

    #直立インデックスファイル
    upright_file = open("{0}/upright.txt".format(base_dir), 'w')

    # ログレベル設定
    logger.setLevel(level[args.verbose])

    verbose = args.verbose

    # 調整用が指定されており、かつ処理対象と違うならば保持
    upright_target = None
    if args.upright_target != args.target and len(args.upright_target) > 0:
        upright_target = args.upright_target

    position_multi_file_to_vmd(position_file, position_gan_file, upright_file, vmd_file, smoothed_file, args.bone, depth_file, start_frame_file, args.centerxy, args.centerz, args.smooth_times, args.threshold_pos, args.threshold_rot, is_ik, args.heelpos, upright_target)
