#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 初期状態の傾きを定義するモーションデータの出力処理
from PyQt5.QtGui import QQuaternion, QVector4D, QVector3D, QMatrix4x4
import logging
import argparse
import glob

from VmdWriter import VmdBoneFrame, VmdInfoIk, VmdShowIkFrame, VmdWriter
from VmdReader import VmdMotion, VmdReader
import pos2vmd_utils

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

level = {0:logging.ERROR,
            1:logging.WARNING,
            2:logging.INFO,
            3:logging.DEBUG}
verbose = 2

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='3d-pose-baseline to vmd')
    parser.add_argument('-t', '--target', dest='target', type=str,
                        help='target directory (motion dir)')
    args = parser.parse_args()

    # VMDモーション読み込み
    reader = VmdReader()

    # ボーン名とボーン情報の辞書リスト
    # bone_sum_dic: 合計用
    # bone_avg_dic: 平均用
    bone_sum_dic = {
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
        "右ひざ":[]
    }
    
    bone_name_dic = {
        "上半身": b'\x8f\xe3\x94\xbc\x90\x67',
        "上半身2": b'\x8f\xe3\x94\xbc\x90\x67\x32',
        "下半身": b'\x89\xba\x94\xbc\x90\x67',
        "首": b'\x8e\xf1',
        "頭": b'\x93\xaa',
        "左肩": b'\x8d\xb6\x8C\xA8',
        "左腕": b'\x8d\xb6\x98\x72',
        "左ひじ": b'\x8d\xb6\x82\xd0\x82\xb6',
        "右肩": b'\x89\x45\x8C\xA8',
        "右腕": b'\x89\x45\x98\x72',
        "右ひじ": b'\x89\x45\x82\xd0\x82\xb6',
        "左足": b'\x8d\xb6\x91\xab',
        "左ひざ": b'\x8d\xb6\x82\xd0\x82\xb4',
        "右足": b'\x89\x45\x91\xab',
        "右ひざ": b'\x89\x45\x82\xd0\x82\xb4'
    }

    # ペアリスト
    bone_pair_list = [
        ["左肩", "右肩"],
        ["左腕", "右腕"],
        ["左ひじ", "右ひじ"],
        ["左足", "右足"],
        ["左ひざ", "右ひざ"]
    ]

    # 単一リスト
    bone_single_list = [
        "上半身",
        "上半身2",
        "下半身",
        "首",
        "頭"
    ]
        
    # モーションのあるディレクトリ内ファイルを読み込む
    for vmdpath in glob.glob("{0}/*.vmd".format(args.target)):
        logger.debug("vmd %s", vmdpath)
        motion = reader.read_vmd_file(vmdpath)

        # モーションの平均を求める
        for bone_name in bone_sum_dic.keys():
            # とりあえずモーションの中身を追加する
            if bone_name in motion.frames:
                # 上半身2とかないやつもあるので、一応チェック
                for f in motion.frames[bone_name]:
                    bone_sum_dic[bone_name].append(f)

    # 回転X,Y,Z
    rotation = QQuaternion()

    bone_avg_dic = {}
    # 複数モーションの平均値を求める
    for k, v_list in bone_sum_dic.items():
        for n, v in enumerate(v_list):
            # rotation += v.rotation

            if n == 0:
                rotation = v.rotation
            else:
                # 線形補間で平均を求める
                rotation = QQuaternion.slerp(rotation, v.rotation, 0.5)

        avg_frame = VmdBoneFrame()
        # 名前はキーのをもらう
        avg_frame.name = bone_name_dic[k]
        # 一応正規化
        avg_frame.rotation = rotation.normalized()

        logger.debug("avg name: %s", k)
        logger.debug("avg rotation all: %s", rotation)
        logger.debug("avg rotation: %s", avg_frame.rotation)
        logger.debug("avg rotation all.toEulerAngles(): %s", rotation.toEulerAngles())
        logger.debug("avg rotation.toEulerAngles(): %s", avg_frame.rotation.toEulerAngles())

        bone_avg_dic[k] = avg_frame

    # 平均リスト
    bone_avg_list = []

    for bone_name in bone_single_list:
        bone_avg_list.append(bone_avg_dic[bone_name])

    # 腕とかは両手の平均とする
    for pair in bone_pair_list:
        left = bone_avg_dic[pair[0]].rotation
        right = bone_avg_dic[pair[1]].rotation

        # 一旦線対称に寄せる
        right2 = QQuaternion(right.scalar(), right.x(), right.y() * -1, right.z() * -1)

        # 線形補間で平均
        rotation = QQuaternion.slerp(left, right2, 0.5)

        logger.debug("left name: %s", pair[0])
        logger.debug("left: %s", left)
        logger.debug("left.toEulerAngles(): %s", left.toEulerAngles())
        logger.debug("right: %s", right)
        logger.debug("right.toEulerAngles(): %s", right.toEulerAngles())
        logger.debug("right2: %s", right2)
        logger.debug("right2.toEulerAngles(): %s", right2.toEulerAngles())
        logger.debug("rotation: %s", rotation)
        logger.debug("rotation.toEulerAngles(): %s", rotation.toEulerAngles())

        # 左側
        left_frame = VmdBoneFrame()
        left_frame.name = bone_avg_dic[pair[0]].name
        left_frame.rotation = rotation

        # 右側
        right_frame = VmdBoneFrame()
        right_frame.name = bone_avg_dic[pair[1]].name
        right_frame.rotation = QQuaternion(rotation.scalar(), rotation.x(), rotation.y() * -1, rotation.z() * -1)

        bone_avg_list.append(left_frame)
        bone_avg_list.append(right_frame)

    # writer.write_vmd_file(vmd_file, bone_frames, showik_frames, expression_frames)
    writer = VmdWriter()
    writer.write_vmd_file("{0}/../upright.vmd".format(args.target), bone_avg_list, pos2vmd_utils.make_showik_frames(False))            
